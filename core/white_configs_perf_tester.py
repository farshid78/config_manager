from __future__ import annotations

import asyncio
import time
import shutil
import socket
import subprocess
import os
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiohttp

from constants import PING_TIMEOUT_SECONDS
from core.logger import get_logger
from core.utils import extract_host, extract_port, detect_protocol
from database.models import ProcessedConfig
from core._white_configs_perf_tester_export_fix import export_perf_results_to_txt

logger = get_logger()

TEST_URL = "https://cp.cloudflare.com/generate_204"
TTFB_TIMEOUT_S = 5.0
ALIVE_CONNECT_TIMEOUT_S = 8.0
STABILITY_ROUNDS = 3
STABILITY_GAP_S = 2.0

MAX_CONCURRENT_DEFAULT = 50


@dataclass(frozen=True)
class PerfResult:
    config_id: int
    protocol: str | None
    server: str | None

    alive: bool
    avg_ttfb_ms: float | None
    stability_success: int
    stability: str
    score: float

    # لینک خام/واترمارک‌شده (برای خروجی txt باید دقیقاً vless://... باشد)
    config_link: str

    details: dict[str, Any]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _safe_kill_process(proc: subprocess.Popen | None, *, timeout_s: float = 5.0) -> None:
    if not proc:
        return
    try:
        if proc.poll() is not None:
            return
        if os.name != "nt":
            proc.send_signal(signal.SIGTERM)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
    except Exception:
        pass


async def _socks5_ttfb_ms(*, socks5_port: int, url: str, timeout_s: float) -> tuple[float | None, str | None]:
    start = time.perf_counter()
    try:
        proxy = f"socks5://127.0.0.1:{socks5_port}"
        timeout = aiohttp.ClientTimeout(total=timeout_s)
        # IMPORTANT: don't use system env proxies (VPN/proxy) during tests
        # This keeps test transport consistent with the in-app SOCKS tunnel only.
        async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as session:
            async with session.get(url, proxy=proxy) as resp:
                await resp.read()
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms, None
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return None, str(exc)


def _stability_score(successes: int) -> int:
    return {3: 100, 2: 60, 1: 20}.get(successes, 0)


def _ttfb_score(avg_ms: float | None) -> int:
    if avg_ms is None:
        return 10
    if avg_ms < 150:
        return 100
    if avg_ms <= 300:
        return 80
    if avg_ms <= 600:
        return 60
    if avg_ms <= 1000:
        return 40
    return 10


def _final_score(*, avg_ttfb_ms: float | None, stability_success: int, alive: bool) -> float:
    if not alive:
        return 0.0
    st = _stability_score(stability_success)
    ttfb = _ttfb_score(avg_ttfb_ms)
    return (ttfb * 0.7) + (st * 0.3)


async def _run_xray_for_config(*, xray_bin: Path, config: str, socks5_port: int, temp_dir: Path) -> subprocess.Popen:
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_cfg = temp_dir / f"xray_run_{socks5_port}.json"

    cfg_text = (config or "").strip()
    if not cfg_text.startswith("{"):
        # فعلاً بدون داشتن template/کانورتر link->xray inbound JSON، نمی‌تونیم xray run -c را برای لینک‌ها واقعی کنیم.
        # این exception با مسیر fallback در _perf_for_one مدیریت می‌شود.
        raise ValueError("non-json config (link)")

    temp_cfg.write_text(cfg_text, encoding="utf-8")

    return subprocess.Popen(
        [str(xray_bin), "run", "-c", str(temp_cfg)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(Path(xray_bin).parent),
    )


def _stability_from_successes(successes: int, rounds: int) -> tuple[int, str]:
    # successes: تعداد دفعاتی که اتصال موفق بوده
    return successes, f"{successes}/{rounds}"


async def _perf_for_one(
    row: ProcessedConfig,
    *,
    semaphore: asyncio.Semaphore,
    top_url: str,
    xray_bin: Path,
    max_alive_timeout_s: float = ALIVE_CONNECT_TIMEOUT_S,
    ttfb_timeout_s: float = TTFB_TIMEOUT_S,
    stability_rounds: int = STABILITY_ROUNDS,
    stability_gap_s: float = STABILITY_GAP_S,
    temp_root: Path,
) -> PerfResult:
    async with semaphore:
        cfg_id = row.id
        protocol = row.protocol
        server = row.host or extract_host(row.raw_config)

        t0 = time.perf_counter()
        logs: list[str] = []

        alive = False
        avg_ttfb_ms: float | None = None
        stability_success = 0

        details: dict[str, Any] = {
            "config_id": cfg_id,
            "server": server,
            "protocol": protocol,
            "timing": {},
            "alive": None,
            "ttfb": [],
            "stability_success": 0,
        }

        temp_dir = temp_root / f"cfg_{cfg_id}" / str(int(time.time() * 1000))
        proc: subprocess.Popen | None = None
        socks_port = _find_free_port()

        cfg_link = (row.watermarked_config or row.raw_config).strip() if row.raw_config else ""

        try:
            if not server:
                return PerfResult(
                    config_id=cfg_id,
                    protocol=protocol,
                    server=None,
                    alive=False,
                    avg_ttfb_ms=None,
                    stability_success=0,
                    stability="0/3",
                    score=0.0,
                    config_link=cfg_link,
                    details={"error": "missing server"},
                )

            details["timing"]["start"] = time.time()

            # 1) تلاش برای اجرای xray perf با JSON
            try:
                proc = await _run_xray_for_config(
                    xray_bin=xray_bin,
                    config=row.raw_config,
                    socks5_port=socks_port,
                    temp_dir=temp_dir,
                )

                start_alive = time.perf_counter()
                while time.perf_counter() - start_alive < max_alive_timeout_s:
                    try:
                        with socket.create_connection(("127.0.0.1", socks_port), timeout=0.5):
                            alive = True
                            break
                    except Exception:
                        await asyncio.sleep(0.2)

                details["timing"]["alive_check_s"] = time.perf_counter() - start_alive
                details["alive"] = alive

                if not alive:
                    return PerfResult(
                        config_id=cfg_id,
                        protocol=protocol,
                        server=server,
                        alive=False,
                        avg_ttfb_ms=None,
                        stability_success=0,
                        stability="0/3",
                        score=0.0,
                        config_link=cfg_link,
                        details={"logs": logs, **details},
                    )

                # واقعی: TTFB از طریق SOCKS5
                ttfb_samples: list[float] = []
                for i in range(stability_rounds):
                    if i > 0:
                        await asyncio.sleep(stability_gap_s)

                    ms, err = await _socks5_ttfb_ms(
                        socks5_port=socks_port, url=top_url, timeout_s=ttfb_timeout_s
                    )
                    if ms is not None and err is None:
                        ttfb_samples.append(float(ms))
                        stability_success += 1
                        details["ttfb"].append({"round": i + 1, "ttfb_ms": ms, "ok": True})
                    else:
                        details["ttfb"].append({"round": i + 1, "ttfb_ms": ms, "ok": False, "error": err})

                avg_ttfb_ms = sum(ttfb_samples) / len(ttfb_samples) if ttfb_samples else None
                details["avg_ttfb_ms"] = avg_ttfb_ms
                details["stability_success"] = stability_success

                score = _final_score(
                    avg_ttfb_ms=avg_ttfb_ms, stability_success=stability_success, alive=alive
                )

                return PerfResult(
                    config_id=cfg_id,
                    protocol=protocol,
                    server=server,
                    alive=alive,
                    avg_ttfb_ms=avg_ttfb_ms,
                    stability_success=stability_success,
                    stability=f"{stability_success}/{stability_rounds}",
                    score=score,
                    config_link=cfg_link,
                    details={"logs": logs, **details, "total_s": time.perf_counter() - t0},
                )
            except ValueError as exc:
                # 2) fallback برای لینک‌ها: با اتصال TCP به host:port “alive” و latency تقریبی می‌سازیم
                # چون xray run -c برای لینک JSON نیست.
                details["error"] = str(exc)
                details["fallback"] = "tcp_connect"

                port = extract_port(row.raw_config)
                if port is None or port == "":
                    port_i = 443
                    details["parsed_port_fallback"] = True
                else:
                    try:
                        port_i = int(port)
                        details["parsed_port_fallback"] = False
                    except Exception:
                        port_i = 443
                        details["parsed_port_fallback"] = True

                details["tcp_target"] = {"host": server, "port": port_i}

                latency_samples: list[float] = []
                for i in range(stability_rounds):
                    if i > 0:
                        await asyncio.sleep(stability_gap_s)

                    start = time.perf_counter()
                    ok = False
                    err_msg: str | None = None
                    try:
                        await asyncio.wait_for(
                            asyncio.open_connection(host=server, port=port_i),
                            timeout=ttfb_timeout_s,
                        )
                        ok = True
                    except Exception as exc:
                        ok = False
                        err_msg = str(exc)
                    finally:
                        elapsed_ms = (time.perf_counter() - start) * 1000.0

                    if ok:
                        latency_samples.append(float(elapsed_ms))
                        stability_success += 1

                    details["ttfb"].append(
                        {
                            "round": i + 1,
                            "ttfb_ms": float(elapsed_ms),
                            "ok": ok,
                            "error": None if ok else err_msg or "tcp_connect_failed",
                        }
                    )

                alive = stability_success > 0
                avg_ttfb_ms = sum(latency_samples) / len(latency_samples) if latency_samples else None
                details["avg_ttfb_ms"] = avg_ttfb_ms
                details["stability_success"] = stability_success

                score = _final_score(
                    avg_ttfb_ms=avg_ttfb_ms, stability_success=stability_success, alive=alive
                )

                return PerfResult(
                    config_id=cfg_id,
                    protocol=protocol or detect_protocol(cfg_link),
                    server=server,
                    alive=alive,
                    avg_ttfb_ms=avg_ttfb_ms,
                    stability_success=stability_success,
                    stability=f"{stability_success}/{stability_rounds}",
                    score=score,
                    config_link=cfg_link,
                    details={"logs": logs, **details, "total_s": time.perf_counter() - t0},
                )

            except Exception as exc:
                logs.append(f"spawn_failed: {exc}")
                details["error"] = str(exc)
                return PerfResult(
                    config_id=cfg_id,
                    protocol=protocol,
                    server=server,
                    alive=False,
                    avg_ttfb_ms=None,
                    stability_success=0,
                    stability="0/3",
                    score=0.0,
                    config_link=cfg_link,
                    details={"logs": logs, **details},
                )

        finally:
            _safe_kill_process(proc)
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


async def evaluate_white_configs(
    *,
    rows: list[ProcessedConfig],
    top_n: int = 100,
    max_concurrency: int = MAX_CONCURRENT_DEFAULT,
    xray_bin_path: Path,
    temp_root: Path,
) -> list[PerfResult]:
    semaphore = asyncio.Semaphore(max_concurrency)

    logger.info(
        "white_perf start | rows={} top_n={} max_concurrency={} xray_bin={}",
        len(rows),
        top_n,
        max_concurrency,
        xray_bin_path.as_posix() if xray_bin_path else None,
    )

    tasks = [
        asyncio.create_task(
            _perf_for_one(
                row,
                semaphore=semaphore,
                top_url=TEST_URL,
                xray_bin=xray_bin_path,
                temp_root=temp_root,
            )
        )
        for row in rows
    ]

    # Incremental progress to avoid "silent hang" perception
    results: list[Any] = []
    total = len(tasks)
    done_count = 0

    try:
        for fut in asyncio.as_completed(tasks):
            r = await fut
            results.append(r)
            done_count += 1
            if done_count == 1 or done_count % 20 == 0 or done_count == total:
                logger.info("white_perf progress | done={}/{}", done_count, total)
    finally:
        # if something goes wrong, ensure tasks are not left running
        for t in tasks:
            if not t.done():
                t.cancel()

    final: list[PerfResult] = []
    for r in results:
        if isinstance(r, PerfResult):
            final.append(r)
        else:
            final.append(
                PerfResult(
                    config_id=-1,
                    protocol=None,
                    server=None,
                    alive=False,
                    avg_ttfb_ms=None,
                    stability_success=0,
                    stability="0/3",
                    score=0.0,
                    config_link="",
                    details={"error": str(r)},
                )
            )

    final.sort(key=lambda x: x.score, reverse=True)
    logger.info("white_perf done | results={}", len(final))
    return final[:top_n]

