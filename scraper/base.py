# scraper/base.py — scraper async از کانال‌های تلگرام

from __future__ import annotations

import aiohttp
from bs4 import BeautifulSoup

from core.logger import get_logger
from processor.parser import ConfigParser
from scraper.sources import SOURCES

logger = get_logger()


class TelegramChannelScraper:
    """جمع‌آوری کانفیگ از پیش‌نمایش عمومی t.me/s/{channel}."""

    def __init__(self):
        self.parser = ConfigParser()

    async def fetch_channel_html(self, channel: str, session: aiohttp.ClientSession) -> str:
        url = f"https://t.me/s/{channel}"
        headers = {"User-Agent": "Mozilla/5.0 ConfigBot/2.0"}
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
            resp.raise_for_status()
            return await resp.text()

    def parse_configs(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.find_all("div", class_="tgme_widget_message_text")
        configs: list[str] = []
        for msg in messages:
            text = msg.get_text()
            configs.extend(self.parser.extract_from_text(text))
        return configs

    async def scrape_source(self, channel: str, session: aiohttp.ClientSession) -> list[str]:
        html = await self.fetch_channel_html(channel, session)
        return self.parse_configs(html)

    async def scrape_all(self, session: aiohttp.ClientSession) -> dict[str, list[str]]:
        """scrape همه منابع — خروجی: {channel: [configs]}"""
        results: dict[str, list[str]] = {}
        for source in SOURCES:
            try:
                configs = await self.scrape_source(source, session)
                results[source] = configs
                logger.info("Scraped {} | configs={}", source, len(configs))
            except Exception as exc:
                logger.error("Scrape failed {} | {}", source, exc)
                results[source] = []
        return results
