# processor/validator.py — اعتبارسنجی، ping و deduplication

from __future__ import annotations

import asyncio

import aiohttp

from constants import PING_TIMEOUT_SECONDS
from core.utils import (
    config_hash,
    detect_protocol,
    extract_host,
    extract_port,
    fetch_country_code,
)
from processor.parser import ConfigParser


class ConfigValidator:
    """اعتبارسنجی کانفیگ: پروتکل، ping TCP، dedup."""

    def __init__(self):
        self.parser = ConfigParser()
        self._seen_hashes: set[str] = set()

    def reset_cache(self) -> None:
        self._seen_hashes.clear()

    async def ping_host(self, host: str, port: int | None) -> bool:
        """تست TCP connect — سریع‌تر از ICMP در محیط cloud."""
        if not host or not port:
            return False
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=PING_TIMEOUT_SECONDS,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def validate_one(
        self,
        config: str,
        session: aiohttp.ClientSession,
        *,
        check_ping: bool = True,
    ) -> dict | None:
        """
        اعتبارسنجی یک کانفیگ.
        None = رد شده (duplicate یا invalid)
        """
        protocol = detect_protocol(config)
        if protocol == "unknown":
            return None

        h = config_hash(config)
        if h in self._seen_hashes:
            return None

        host = extract_host(config)
        port = extract_port(config)

        if check_ping and host and port:
            alive = await self.ping_host(host, port)
            if not alive:
                return None

        country = "UN"
        if host:
            country = await fetch_country_code(host, session)

        watermarked = self.parser.inject_watermark(config, country)

        self._seen_hashes.add(h)

        return {
            "raw_config": config,
            "watermarked_config": watermarked,
            "config_hash": h,
            "country_code": country,
            "protocol": protocol,
            "host": host,
        }

    async def validate_batch(
        self,
        configs: list[str],
        session: aiohttp.ClientSession,
        *,
        check_ping: bool = True,
    ) -> list[dict]:
        """اعتبارسنجی دسته‌ای."""
        results = []
        for config in configs:
            item = await self.validate_one(config, session, check_ping=check_ping)
            if item:
                results.append(item)
        return results
