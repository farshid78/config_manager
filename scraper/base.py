# scraper/base.py — اسکرپر ناهمزمان و مقاوم برای جمع‌آوری کانفیگ از کانال‌های تلگرام
# از پیش‌نمایش عمومی t.me/s/{channel} استفاده می‌شود (بدون نیاز به لاگین)
# شامل: تلاش مجدد با backoff، حذف تکراری، پارس HTML انعطاف‌پذیر

from __future__ import annotations

import asyncio
import random
import re
from html import unescape
from typing import Iterable

import aiohttp
from bs4 import BeautifulSoup

from core.logger import get_logger
from core.utils import config_hash
from processor.parser import ConfigParser
from scraper.sources import TELEGRAM_SOURCES

logger = get_logger()

# الگوی regex بهبودیافته برای استخراج کانفیگ‌ها
# پشتیبانی از: vmess://, vless://, trojan://, ss://
# مهم: vmess حاوی Base64 است (شامل = و + و /)
# vless/trojan/ss حاوی query params با & و #fragment هستند
CONFIG_REGEX = re.compile(
    r"(vmess://[A-Za-z0-9+/=_-]+(?:#[^\s]*)?|"
    r"vless://[^\s]+?#[^\s]*|"
    r"vless://[^\s]+?(?=\s|$)|"
    r"trojan://[^\s]+?#[^\s]*|"
    r"trojan://[^\s]+?(?=\s|$)|"
    r"ss://[A-Za-z0-9+/=_-]+@[^\s]+?#[^\s]*|"
    r"ss://[A-Za-z0-9+/=_-]+@[^\s]+?(?=\s|$)|"
    r"ss://[A-Za-z0-9+/=_-]+#[^\s]*|"
    r"ss://[A-Za-z0-9+/=_-]+(?=\s|$))",
    re.IGNORECASE,
)


class TelegramChannelScraper:
    """اسکرپر کانفیگ از پیش‌نمایش عمومی کانال‌های تلگرام.

    از آدرس t.me/s/{channel} برای دسترسی به پیام‌های عمومی استفاده می‌کند.

    ویژگی‌ها:
    - استخراج کانفیگ با regex بهبودیافته از متن و HTML
    - پارس HTML انعطاف‌پذیر (پشتیبانی از تگ‌های <pre> و <a>)
    - تبدیل HTML entities (&amp; -> &)
    - حذف تکراری سریع در سطح اسکرپر
    - تلاش مجدد با exponential backoff + jitter
    - لاگ‌گیری دقیق خطاها
    """

    def __init__(self):
        """مقداردهی اولیه اسکرپر."""
        self.parser = ConfigParser()

    async def fetch_channel_html(
        self,
        channel: str,
        session: aiohttp.ClientSession,
        *,
        timeout_seconds: int = 20,
        retries: int = 3,
    ) -> str:
        """دریافت HTML پیش‌نمایش عمومی کانال تلگرام.

        در صورت خطا، با exponential backoff + jitter تلاش مجدد می‌شود.
        اگر پروکسی در تنظیمات تعریف شده باشد، از آن استفاده می‌کند.

        Args:
            channel: نام کانال (بدون @)
            session: نشست HTTP ناهمزمان
            timeout_seconds: مهلت درخواست (ثانیه)
            retries: حداکثر تعداد تلاش مجدد
        Returns:
            HTML صفحه پیش‌نمایش
        Raises:
            Exception: آخرین خطا در صورت شکست تمام تلاش‌ها
        """
        from core.config import get_settings

        url = f"https://t.me/s/{channel}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        # دریافت پروکسی از تنظیمات (اگر تنظیم شده باشد)
        settings = get_settings()
        proxy = settings.scraper_proxy.strip() if settings.scraper_proxy else None
        if proxy:
            logger.debug("Using proxy {} for {}", proxy, channel)

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=timeout_seconds)
                async with session.get(url, headers=headers, timeout=timeout, proxy=proxy) as resp:
                    resp.raise_for_status()
                    html = await resp.text()
                    logger.debug("Fetched {} | status={} | length={}", channel, resp.status, len(html))
                    return html
            except Exception as exc:
                last_exc = exc
                logger.warning("Fetch attempt {}/{} failed for {}: {}", attempt + 1, retries + 1, channel, exc)
                if attempt >= retries:
                    break
                await asyncio.sleep((0.8 + random.random()) * (2 ** attempt))

        assert last_exc is not None
        logger.error("All fetch attempts failed for {}: {}", channel, last_exc)
        raise last_exc

    def _clean_html_to_text(self, html_fragment: str) -> str:
        """تبدیل HTML به متن خام با حفظ محتوا.

        - حذف تگ‌های HTML
        - تبدیل HTML entities (&amp; -> &)
        - پاک‌سازی فاصله‌های اضافی

        Args:
            html_fragment: قطعه HTML
        Returns:
            متن تمیز شده
        """
        text = re.sub(r"<[^>]+>", "", html_fragment)
        text = unescape(text)
        text = re.sub(r"[ 	]+", " ", text)
        return text.strip()

    def _extract_text_nodes(self, html: str) -> Iterable[str]:
        """استخراج گره‌های متنی کاندید از HTML تلگرام.

        سه حالت بررسی می‌شود:
        1. تگ‌های <pre> داخل پیام‌ها (کانفیگ‌ها معمولا داخل pre هستند)
        2. div با کلاس tgme_widget_message_text (متن کامل پیام)
        3. fallback: کل متن صفحه

        Args:
            html: HTML صفحه پیش‌نمایش
        Yields:
            رشته‌های متنی حاوی کانفیگ‌های احتمالی
        """
        soup = BeautifulSoup(html, "html.parser")

        # حالت 1: تگ‌های <pre> — بهترین منبع کانفیگ
        pre_tags = soup.find_all("pre")
        for pre in pre_tags:
            text = pre.get_text(strip=True)
            if text and any(text.startswith(p) for p in ("vmess://", "vless://", "trojan://", "ss://")):
                yield text

        # حالت 2: متن کامل هر پیام (با تبدیل HTML entities)
        for msg in soup.find_all("div", class_="tgme_widget_message_text"):
            inner_html = str(msg)
            text = self._clean_html_to_text(inner_html)
            if text:
                yield text

        # حالت 3: fallback — کل صفحه
        if not soup.find_all("div", class_="tgme_widget_message_text"):
            text = soup.get_text("\n", strip=True)
            if text:
                yield text

    def _extract_configs_from_html(self, html: str) -> list[str]:
        """استخراج مستقیم کانفیگ‌ها از HTML خام.

        این روش مستقیما روی HTML جستجو می‌کند و HTML entities رو
        بعد از استخراج تبدیل می‌کند.

        Args:
            html: HTML خام صفحه
        Returns:
            لیست کانفیگ‌های استخراج‌شده
        """
        configs = []
        soup = BeautifulSoup(html, "html.parser")

        # تگ‌های <pre> — بهترین منبع
        for pre in soup.find_all("pre"):
            text = pre.get_text(strip=True)
            if any(text.startswith(p) for p in ("vmess://", "vless://", "trojan://", "ss://")):
                text = unescape(text)
                matches = CONFIG_REGEX.findall(text)
                configs.extend(matches)

        # متن کامل هر پیام
        for msg in soup.find_all("div", class_="tgme_widget_message_text"):
            inner = str(msg)
            clean = self._clean_html_to_text(inner)
            matches = CONFIG_REGEX.findall(clean)
            configs.extend(matches)

        return configs

    def parse_configs(self, html: str) -> list[str]:
        """استخراج و حذف تکراری کانفیگ‌ها از HTML.

        از هر دو روش استخراج از متن و استخراج مستقیم HTML استفاده می‌کند
        تا بیشترین تعداد کانفیگ‌ها رو پیدا کنه.

        Args:
            html: HTML صفحه پیش‌نمایش
        Returns:
            لیست کانفیگ‌های یکتا
        """
        configs: list[str] = []
        seen: set[str] = set()

        # روش 1: استخراج از گره‌های متنی (با BeautifulSoup)
        for text in self._extract_text_nodes(html):
            for cfg in self.parser.extract_from_text(text):
                h = config_hash(cfg)
                if h not in seen:
                    seen.add(h)
                    configs.append(cfg)

        # روش 2: استخراج مستقیم از HTML (برای پوشش بیشتر)
        for cfg in self._extract_configs_from_html(html):
            h = config_hash(cfg)
            if h not in seen:
                seen.add(h)
                configs.append(cfg)

        logger.debug("parse_configs: found {} unique configs", len(configs))
        return configs

    async def scrape_source(
        self,
        channel: str,
        session: aiohttp.ClientSession,
        *,
        max_configs: int | None = 2000,
    ) -> list[str]:
        """جمع‌آوری کانفیگ‌ها از یک کانال منبع.

        Args:
            channel: نام کانال (بدون @)
            session: نشست HTTP ناهمزمان
            max_configs: حداکثر تعداد کانفیگ
        Returns:
            لیست کانفیگ‌های استخراج‌شده
        """
        try:
            html = await self.fetch_channel_html(channel, session)
        except Exception as exc:
            logger.error("Cannot fetch channel {}: {}", channel, exc)
            return []

        if not html:
            logger.warning("Empty HTML for channel {}", channel)
            return []

        configs = self.parse_configs(html)
        logger.info("Scraped {} | configs={}", channel, len(configs))

        if max_configs is not None:
            return configs[:max_configs]
        return configs

    async def scrape_all(self, session: aiohttp.ClientSession) -> dict[str, list[str]]:
        """جمع‌آوری کانفیگ‌ها از تمام منابع (دیتابیس + فایل).

        ابتدا منابع فعال از دیتابیس خوانده می‌شوند.
        اگر دیتابیس خالی باشد، از منابع پیش‌فرض فایل sources.py استفاده می‌شود.
        در صورت خطا در یک منبع، لاگ خطا ثبت شده و ادامه داده می‌شود.

        Args:
            session: نشست HTTP ناهمزمان
        Returns:
            دیکشنری {نام_منبع: [لیست_کانفیگ‌ها]}
        """
        from scraper.subscription import SubscriptionScraper
        from database.session import get_session_factory
        from database import crud

        results: dict[str, list[str]] = {}
        total_configs = 0

        # ─── خواندن منابع فعال از دیتابیس ───
        factory = get_session_factory()
        db_sources = []
        try:
            async with factory() as db_session:
                db_sources = await crud.get_active_scraper_sources(db_session)
        except Exception as exc:
            logger.warning("Failed to read sources from DB: {} — using defaults", exc)

        # اگر دیتابیس خالی بود، از منابع پیش‌فرض استفاده کن
        if not db_sources:
            logger.info("DB sources empty — using default file sources")
            # اسکرپ کانال‌های تلگرام پیش‌فرض
            for source in TELEGRAM_SOURCES:
                try:
                    configs = await self.scrape_source(source.url, session)
                    results[source.name] = configs
                    total_configs += len(configs)
                    logger.info("Scraped telegram {} | configs={}", source.name, len(configs))
                except Exception as exc:
                    logger.error("Scrape telegram {} failed: {}", source.name, exc)
                    results[source.name] = []

            # اسکرپ منابع اشتراک پیش‌فرض
            sub_scraper = SubscriptionScraper()
            from scraper.sources import SUBSCRIPTION_SOURCES
            for source in SUBSCRIPTION_SOURCES:
                try:
                    configs = await sub_scraper.scrape_subscription(source, session)
                    results[source.name] = configs
                    total_configs += len(configs)
                    logger.info("Scraped subscription {} | configs={}", source.name, len(configs))
                except Exception as exc:
                    logger.error("Scrape subscription {} failed: {}", source.name, exc)
                    results[source.name] = []
        else:
            # اسکرپ از منابع دیتابیس
            sub_scraper = SubscriptionScraper()
            for src in db_sources:
                try:
                    if src.source_type == "telegram":
                        configs = await self.scrape_source(src.url, session)
                    elif src.source_type == "subscription":
                        from scraper.sources import Source
                        source_obj = Source(name=src.name, url=src.url, source_type=src.source_type)
                        configs = await sub_scraper.scrape_subscription(source_obj, session)
                    else:
                        logger.warning("Unknown source type: {} — skipped", src.source_type)
                        continue

                    results[src.name] = configs
                    total_configs += len(configs)
                    logger.info("Scraped {} ({}) | configs={}", src.name, src.source_type, len(configs))

                    # به‌روزرسانی آمار در دیتابیس
                    try:
                        async with factory() as db_session:
                            await crud.update_scraper_source_stats(db_session, src.url, len(configs))
                    except Exception as exc:
                        logger.warning("Failed to update stats for {}: {}", src.name, exc)

                except Exception as exc:
                    logger.error("Scrape {} failed: {}", src.name, exc)
                    results[src.name] = []

        logger.info(
            "اسکرپ تمام منابع انجام شد | کل کانفیگ‌ها={}",
            total_configs,
        )
        return results
