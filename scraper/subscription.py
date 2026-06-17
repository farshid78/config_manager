# scraper/subscription.py — اسکرپر منابع اشتراک (Subscription)
# پشتیبانی از لینک‌های raw و Base64-encoded
# شامل: تلاش مجدد، تشخیص خودکار Base64، لاگ‌گیری فارسی

from __future__ import annotations

import asyncio
import base64
import random
import re

import aiohttp

from constants import CONFIG_PATTERN
from core.config import get_settings
from core.logger import get_logger
from core.utils import config_hash
from processor.parser import ConfigParser
from scraper.sources import Source

logger = get_logger()


class SubscriptionScraper:
    """اسکرپر کانفیگ از منابع اشتراک (Subscription).

    منابع اشتراک لینک‌هایی هستند که فایل متنی حاوی کانفیگ ارائه می‌دهند.
    محتوا ممکن است:
    - متن خام حاوی کانفیگ‌ها (vmess://, vless://, trojan://, ss://)
    - Base64-encoded باشد (یک رشته طولانی Base64)
    - ترکیبی از هر دو

    ویژگی‌ها:
    - تشخیص خودکار Base64 و رمزگشایی
    - پشتیبانی از پروکسی
    - تلاش مجدد با exponential backoff
    - حذف تکراری
    """

    def __init__(self):
        self.parser = ConfigParser()

    def _get_proxy(self) -> str | None:
        """دریافت پروکسی از تنظیمات."""
        settings = get_settings()
        proxy = settings.scraper_proxy.strip() if settings.scraper_proxy else None
        return proxy

    async def fetch_subscription(
        self,
        source: Source,
        session: aiohttp.ClientSession,
        *,
        timeout_seconds: int = 30,
        retries: int = 3,

    ) -> str:
        """دریافت محتوای منبع اشتراک.

        Args:
            source: منبع اشتراک
            session: نشست HTTP ناهمزمان
            timeout_seconds: مهلت درخواست (ثانیه)
            retries: حداکثر تعداد تلاش مجدد
        Returns:
            محتوای خام منبع
        Raises:
            Exception: آخرین خطا در صورت شکست
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/plain,application/octet-stream,*/*",
            "Accept-Language": "en-US,en;q=0.5",
        }

        proxy = self._get_proxy()
        if proxy:
            logger.debug("Using proxy {} for {}", proxy, source.name)

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                timeout = aiohttp.ClientTimeout(total=timeout_seconds)
                async with session.get(
                    source.url,
                    headers=headers,
                    timeout=timeout,
                    proxy=proxy,
                ) as resp:
                    resp.raise_for_status()
                    content = await resp.text()
                    logger.debug(
                        "دریافت {} | وضعیت={} | حجم={}",
                        source.name,
                        resp.status,
                        len(content),
                    )
                    return content
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "تلاش {}/{} ناموفق برای {}: {}",
                    attempt + 1,
                    retries + 1,
                    source.name,
                    exc,
                )
                if attempt >= retries:
                    break
                await asyncio.sleep((0.8 + random.random()) * (2 ** attempt))

        assert last_exc is not None
        logger.error("All attempts failed for {}: {}", source.name, last_exc)
        raise last_exc

    def _decode_base64_content(self, content: str) -> str:
        """رمزگشایی محتوای Base64.

        اگر محتوا Base64-encoded باشد، آن را رمزگشایی می‌کند.
        اگر نباشد، همان محتوا را برمی‌گرداند.

        Args:
            content: محتوای خام
        Returns:
            محتوای رمزگشایی‌شده یا همان محتوا
        """
        content = content.strip()

        # اگر محتوا مستقیما شامل پروتکل‌هاست، نیاز به رمزگشایی نیست
        if any(content.startswith(p) for p in ("vmess://", "vless://", "trojan://", "ss://")):
            return content

        # اگر محتوا شامل پروتکل‌ها در وسطش هست
        if any(p in content for p in ("vmess://", "vless://", "trojan://", "ss://")):
            return content

        # تلاش برای رمزگشایی Base64
        try:
            # حذف فاصله‌ها و newline ها
            clean = content.replace("\n", "").replace("\r", "").replace(" ", "")

            # اضافه کردن padding اگر لازم بود
            padding = len(clean) % 4
            if padding:
                clean += "=" * (4 - padding)

            decoded = base64.b64decode(clean).decode("utf-8", errors="ignore")

            # بررسی اینکه آیا خروجی حاوی کانفیگ هست
            if any(p in decoded for p in ("vmess://", "vless://", "trojan://", "ss://")):
                logger.debug("Base64 content decoded successfully")
                return decoded
            else:
                logger.debug("Base64 decoded but no configs found")
                return content
        except Exception as exc:
            logger.debug("Base64 decode failed: {}", exc)
            return content

    def _extract_configs(self, content: str) -> list[str]:
        """استخراج کانفیگ‌ها از محتوای منبع اشتراک.

        ابتدا Base64 رمزگشایی می‌شود، سپس با regex کانفیگ‌ها استخراج می‌شوند.

        Args:
            content: محتوای خام یا رمزگشایی‌شده
        Returns:
            لیست کانفیگ‌های استخراج‌شده
        """
        # رمزگشایی Base64 اگر لازم بود
        decoded = self._decode_base64_content(content)

        # استخراج با regex
        configs = re.findall(CONFIG_PATTERN, decoded)

        # همچنین از parser استفاده کن (برای پوشش بیشتر)
        parser_configs = self.parser.extract_from_text(decoded)

        # ترکیب و حذف تکراری
        all_configs: list[str] = []
        seen: set[str] = set()

        for cfg in configs + parser_configs:
            h = config_hash(cfg)
            if h not in seen:
                seen.add(h)
                all_configs.append(cfg)

        return all_configs

    async def scrape_subscription(
        self,
        source: Source,
        session: aiohttp.ClientSession,
        *,
        max_configs: int | None = 5000,
    ) -> list[str]:
        """جمع‌آوری کانفیگ‌ها از یک منبع اشتراک.

        Args:
            source: منبع اشتراک
            session: نشست HTTP ناهمزمان
            max_configs: حداکثر تعداد کانفیگ
        Returns:
            لیست کانفیگ‌های استخراج‌شده
        """
        try:
            content = await self.fetch_subscription(source, session)
        except Exception as exc:
            logger.error("Fetch subscription {} failed: {}", source.name, exc)
            return []

        if not content:
            logger.warning("Empty content for subscription {}", source.name)
            return []

        configs = self._extract_configs(content)
        logger.info("Scraped subscription {} | configs={}", source.name, len(configs))

        if max_configs is not None:
            return configs[:max_configs]
        return configs

    async def scrape_all_subscriptions(
        self,
        session: aiohttp.ClientSession,
    ) -> dict[str, list[str]]:
        """جمع‌آوری کانفیگ‌ها از تمام منابع اشتراک.

        Args:
            session: نشست HTTP ناهمزمان
        Returns:
            دیکشنری {نام_منبع: [لیست_کانفیگ‌ها]}
        """
        from scraper.sources import SUBSCRIPTION_SOURCES

        results: dict[str, list[str]] = {}
        total_configs = 0

        for source in SUBSCRIPTION_SOURCES:
            try:
                configs = await self.scrape_subscription(source, session)
                results[source.name] = configs
                total_configs += len(configs)
                logger.info(
                    "اسکرپ اشتراک {} | کانفیگ‌ها={}",
                    source.name,
                    len(configs),
                )
            except Exception as exc:
                logger.error("Scrape subscription {} failed: {}", source.name, exc)
                results[source.name] = []

        logger.info(
            "اسکرپ تمام اشتراک‌ها انجام شد | منابع={} | کل کانفیگ‌ها={}",
            len(SUBSCRIPTION_SOURCES),
            total_configs,
        )
        return results
