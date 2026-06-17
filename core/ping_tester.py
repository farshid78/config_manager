from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Iterable

from core.logger import get_logger
from core.utils import extract_host, extract_port
from database.models import ProcessedConfig
from constants import PING_TIMEOUT_SECONDS

logger = get_logger()


@dataclass(frozen=True)
class PingResult:
    config_id: int
    host: str
    port: int
    latency_ms: float
    ok: bool
    error: str | None = None


def _parse_host_port_from_db_row(row: ProcessedConfig) -> tuple[str | None, int | None]:
    """Try to find host/port from DB row.

    DB currently stores `host` only for some cases.
    We also parse from raw_config for port fallback.
    """
    host = row.host or extract_host(row.raw_config)
    port = extract_port(row.raw_config)
    return host, port


async def _tcp_latency_ms(host: str, port: int, timeout_s: float) -> tuple[float, str | None]:
    """Measure TCP connect latency.

    We don't rely on ICMP ping because it's often unavailable.
    """
    start = time.perf_counter()
    try:
        fut = asyncio.open_connection(host=host, port=port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout_s)
        # close immediately
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms, None
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms, str(exc)


def _is_valid_host(host: str | None) -> bool:
    if not host:
        return False
    host = host.strip()
    if not host:
        return False
    # avoid obvious placeholders
    if host.lower() in {"unknown", "none"}:
        return False
    return True


async def test_configs_latency(
    configs: Iterable[ProcessedConfig],
    *,
    threshold_ms: float,
    timeout_s: float = PING_TIMEOUT_SECONDS,
    max_concurrency: int = 40,
) -> tuple[list[tuple[ProcessedConfig, PingResult]], list[tuple[ProcessedConfig, PingResult]]]:
    """Test latency for each config and split into (passed, failed).

    Passed means ok == True AND latency_ms <= threshold_ms.
    Failed includes non-ok or latency > threshold.
    """

    sem = asyncio.Semaphore(max_concurrency)
    passed: list[tuple[ProcessedConfig, PingResult]] = []
    failed: list[tuple[ProcessedConfig, PingResult]] = []

    async def _worker(row: ProcessedConfig):
        async with sem:
            host, port = _parse_host_port_from_db_row(row)
            if not _is_valid_host(host):
                pr = PingResult(
                    config_id=row.id,
                    host=host or "",
                    port=port or 443,
                    latency_ms=float("inf"),
                    ok=False,
                    error="missing host",
                )
                failed.append((row, pr))
                return

            try:
                port_i = int(port) if port else 443
            except Exception:
                port_i = 443

            latency_ms, err = await _tcp_latency_ms(host=host, port=port_i, timeout_s=timeout_s)
            ok = err is None
            pr = PingResult(
                config_id=row.id,
                host=host,
                port=port_i,
                latency_ms=latency_ms,
                ok=ok,
                error=err,
            )

            if ok and latency_ms <= threshold_ms:
                passed.append((row, pr))
            else:
                failed.append((row, pr))

    tasks = [asyncio.create_task(_worker(row)) for row in configs]
    if tasks:
        await asyncio.gather(*tasks)

    passed.sort(key=lambda x: x[1].latency_ms)
    failed.sort(key=lambda x: x[1].latency_ms)
    return passed, failed


def format_export_text(
    operator_title: str,
    threshold_ms: float,
    passed: list[tuple[ProcessedConfig, PingResult]],
) -> str:
    header = (
        "# white-configs-latency\n"
        f"# operator: {operator_title}\n"
        f"# threshold_ms: {threshold_ms}\n"
        f"# passed_count: {len(passed)}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
    )

    blocks: list[str] = []
    for row, pr in passed:
        config_text = row.watermarked_config or row.raw_config
        # Ensure we only show the config string, plus a readable comment header.
        # Telegram config formats often include newlines; keep them.
        blocks.append(
            f"# id:{row.id} latency_ms:{pr.latency_ms:.1f} host:{pr.host}:{pr.port}"
            f"\n{config_text}"
        )

    return header + "\n\n" + "\n\n".join(blocks) if blocks else header


async def export_white_configs_latency_to_file(
    *,
    operator_title: str,
    threshold_ms: float,
    rows: list[ProcessedConfig],
    export_path,
    timeout_s: float = PING_TIMEOUT_SECONDS,
) -> tuple[int, int]:
    """Run tests and write txt file. Returns (passed_count, tested_count)."""

    passed, _failed = await test_configs_latency(rows, threshold_ms=threshold_ms, timeout_s=timeout_s)

    text = format_export_text(operator_title=operator_title, threshold_ms=threshold_ms, passed=passed)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    with open(export_path, "w", encoding="utf-8") as f:
        f.write(text)

    return len(passed), len(rows)

