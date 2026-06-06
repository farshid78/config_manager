# scraper/base.py — Scraper async و مقاوم برای تلگرام

from __future__ import annotations

import asyncio
import random
from typing import Iterable

import aiohttp
from bs4 import BeautifulSoup

from core.logger import get_logger
from core.utils import config_hash
from processor.parser import ConfigParser
from scraper.sources import SOURCES

logger = get_logger()


class TelegramChannelScraper:
    """جمع‌آوری کانفیگ از پیش‌نمایش عمومی t.me/s/{channel}.

    نکته:
    - استخراج کانفیگ را با regex روی متن انجام می‌دهیم (CONFIG_PATTERN).
    - HTML تلگرام ممکن است ساختار متفاوتی داشته باشد؛ پس parse را انعطاف‌پذیر می‌کنیم.
    - Dedup سریع در level scraper انجام می‌شود تا validator کمتر کار کند.
    """

    def __init__(self):
        self.parser = ConfigParser()

    async def fetch_channel_html(
        self,
        channel: str,
        session: aiohttp.ClientSession,
        *,
        timeout_seconds: int = 20,
        retries: int = 3,
    ) -> str:
        url = f"https://t.me/s/{channel}"
        headers = {
            "User-Agent": "Mozilla/5.0 ConfigBot/2.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=timeout_seconds)
                async with session.get(url, headers=headers, timeout=timeout) as resp:
                    resp.raise_for_status()
                    return await resp.text()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= retries:
                    break
                # backoff + jitter
                await asyncio.sleep((0.8 + random.random()) * (2**attempt))

        assert last_exc is not None
        raise last_exc

    def _extract_text_nodes(self, html: str) -> Iterable[str]:
        """متن‌های کاندید برای استخراج کانفیگ را تولید می‌کند."""
        soup = BeautifulSoup(html, "html.parser")

        # حالت 1: ساختار رایج تلگرام
        for msg in soup.find_all("div", class_="tgme_widget_message_text"):
            text = msg.get_text("\n", strip=True)
            if text:
                yield text

        # حالت 2: اگر حالت بالا چیزی پیدا نکند، کل صفحه را sanitize می‌کنیم
        # (این کمک می‌کند در صورت تغییر DOM تلگرام همچنان استخراج کنیم)
        if not any(True for _ in soup.find_all("div", class_="tgme_widget_message_text")):
            text = soup.get_text("\n", strip=True)
            if text:
                yield text

    def parse_configs(self, html: str) -> list[str]:
        """استخراج کانفیگ‌ها از HTML."""
        configs: list[str] = []
        seen: set[str] = set()  # dedup by config_hash

        for text in self._extract_text_nodes(html):
            for cfg in self.parser.extract_from_text(text):
                h = config_hash(cfg)
                if h in seen:
                    continue
                seen.add(h)
                configs.append(cfg)

        return configs

    async def scrape_source(
        self,
        channel: str,
        session: aiohttp.ClientSession,
        *,
        max_configs: int | None = 2000,
    ) -> list[str]:
        html = await self.fetch_channel_html(channel, session)
        configs = self.parse_configs(html)
        if max_configs is not None:
            return configs[:max_configs]
        return configs

    async def scrape_all(self, session: aioiohttp.ClientSession) -> dict[str, list[str]]:
        """scrape همه منابع — خروجی: {source: [configs]}"""
        results: dict[str, list[str]] = {}

        for source in SOURCES:
            try:
                configs = await self.scrape_source(source, session)
                results[source] = configs
                logger.info("Scraped {} | configs={}", source, len(configs))
            except Exception as exc:  # noqa: BLE001
                logger.error("Scrape failed {} | {}", source, exc)
                results[source] = []

        return results

