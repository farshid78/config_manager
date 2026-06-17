from __future__ import annotations

import time
from typing import Any


def export_perf_results_to_txt(*, operator: str, results: list[Any]) -> str:
    header = [
        "# white-configs-perf",
        f"# operator: {operator}",
        f"# generated_at: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        "━━━━━━━━━━━━━━━━━━━━",
        "# each line is a raw config link (v2ray/vless compatible)",
    ]

    lines: list[str] = []
    for r in results:
        cfg = (getattr(r, "config_link", "") or "").strip()
        if not cfg:
            continue
        if getattr(r, "alive", False):
            lines.append(cfg)

    return "\n".join(header + lines) + "\n"

