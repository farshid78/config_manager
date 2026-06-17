# processor/validator.py — اعتبارسنجی کانفیگ‌ها: بررسی پروتکل، تست اتصال (ping)، حذف تکراری
# این ماژول کانفیگ‌ها را فیلتر کرده و فقط کانفیگ‌های معتبر را عبور می‌دهد

from __future__ import annotations

import asyncio

import aiohttp

from constants import PING_TIMEOUT_SECONDS
from core.logger import get_logger
from core.utils import (
    config_hash,
    detect_protocol,
    extract_host,
    extract_port,
    fetch_country_code,
)
from processor.parser import ConfigParser

logger = get_logger()


class ConfigValidator:
    """کلاس اعتبارسنجی کانفیگ‌های V2Ray.

    مراحل اعتبارسنجی:
    1. تشخیص پروتکل — رد کردن پروتکل‌های ناشناخته
    2. بررسی تکراری — مقایسه هش با لیست دیده‌شده‌ها
    3. تست اتصال (ping) — بررسی دسترسی‌پذیری سرور (اختیاری)
    4. تشخیص کشور — دریافت کد کشور از ip-api
    5. واترمارک — تزریق نام کانال به کانفیگ
    """

    def __init__(self):
        """مقداردهی اولیه اعتبارسنج."""
        self.parser = ConfigParser()
        self._seen_hashes: set[str] = set()
        self._country_cache: dict[str, str] = {}  # کش کشور بر اساس host/IP

    def reset_cache(self) -> None:
        """پاک‌سازی کش هش‌ها — استفاده بین batch‌های مختلف."""
        self._seen_hashes.clear()

    async def ping_host(self, host: str, port: int | None) -> bool:
        """تست اتصال TCP به سرور — سریع‌تر از ICMP در محیط cloud.

        سعی می‌کند یک اتصال TCP به host:port برقرار کند.
        اگر اتصال در مهلت زمانی برقرار شود، سرور فعال است.

        Args:
            host: آدرس سرور (IP یا hostname)
            port: شماره پورت سرور
        Returns:
            True اگر سرور قابل دسترسی باشد، False در غیر این صورت
        """
        if not host or not port:  # اگر host یا port خالی بود
            return False  # سرور قابل تست نیست
        try:
            # تلاش برای اتصال TCP با مهلت زمانی
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),  # اتصال TCP
                timeout=PING_TIMEOUT_SECONDS,  # مهلت زمانی (ثانیه)
            )
            writer.close()  # بستن اتصال
            await writer.wait_closed()  # انتظار برای بسته شدن کامل
            return True  # سرور قابل دسترسی است
        except Exception:  # خطای اتصال (timeout, refused, ...)
            return False  # سرور غیرقابل دسترسی

    async def validate_one(
        self,
        config: str,
        session: aiohttp.ClientSession,
        *,
        check_ping: bool = True,
    ) -> dict | None:
        """اعتبارسنجی یک کانفیگ V2Ray.

        مراحل:
        1. تشخیص پروتکل — رد کردن کانفیگ‌های ناشناخته
        2. بررسی تکراری — مقایسه هش با کش داخلی
        3. تست اتصال — اگر check_ping فعال باشد
        4. تشخیص کشور — از ip-api.com
        5. واترمارک — تزریق نام کانال

        Args:
            config: رشته کانفیگ V2Ray
            session: نشست HTTP برای درخواست ip-api
            check_ping: آیا تست اتصال انجام شود (پیش‌فرض: True)
        Returns:
            دیکشنری اطلاعات کانفیگ یا None اگر رد شده باشد
        """
        # مرحله 1: تشخیص پروتکل
        protocol = detect_protocol(config)  # تشخیص نوع پروتکل
        if protocol == "unknown":  # اگر پروتکل ناشناخته بود
            return None  # رد کردن کانفیگ

        # مرحله 2: بررسی تکراری
        h = config_hash(config)  # محاسبه هش کانفیگ
        if h in self._seen_hashes:  # اگر هش قبلاً دیده شده
            return None  # رد کردن کانفیگ تکراری

        # مرحله 3: استخراج اطلاعات سرور
        host = extract_host(config)  # استخراج آدرس سرور
        port = extract_port(config)  # استخراج شماره پورت

        # مرحله 4: تست اتصال (اختیاری)
        if check_ping and host and port:  # اگر ping فعال و اطلاعات کامل بود
            alive = await self.ping_host(host, port)  # تست اتصال TCP
            if not alive:  # اگر سرور پاسخ نداد
                return None  # رد کردن کانفیگ غیرفعال

        # مرحله 5: تشخیص کشور (با کش محلی برای سرعت بیشتر)
        country = "UN"
        if host:
            # بررسی کش محلی اول
            if host in self._country_cache:
                country = self._country_cache[host]
            else:
                country = await fetch_country_code(host, session)
                self._country_cache[host] = country

        # مرحله 6: واترمارک
        watermarked = self.parser.inject_watermark(config, country)  # تزریق واترمارک

        # ثبت هش در کش
        self._seen_hashes.add(h)  # اضافه کردن هش به لیست دیده‌شده‌ها

        # بازگرداندن اطلاعات کانفیگ معتبر
        return {
            "raw_config": config,  # متن اصلی کانفیگ
            "watermarked_config": watermarked,  # کانفیگ با واترمارک
            "config_hash": h,  # هش MD5
            "country_code": country,  # کد کشور
            "protocol": protocol,  # نوع پروتکل
            "host": host,  # آدرس سرور
        }

    async def validate_batch(
        self,
        configs: list[str],
        session: aiohttp.ClientSession,
        *,
        check_ping: bool = True,
        max_concurrent: int = 10,
    ) -> list[dict]:
        """اعتبارسنجی دسته‌ای همزمان کانفیگ‌ها.

        از asyncio.Semaphore برای محدودسازی همزمانی استفاده می‌شود
        تا از ارسال بیش از حد درخواست به ip-api جلوگیری شود.

        Args:
            configs: لیست رشته‌های کانفیگ
            session: نشست HTTP برای درخواست ip-api
            check_ping: آیا تست اتصال انجام شود (پیش‌فرض: True)
            max_concurrent: حداکثر تعداد اعتبارسنجی همزمان (پیش‌فرض: 10)
        Returns:
            لیست دیکشنری‌های کانفیگ‌های معتبر
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _validate_with_semaphore(config: str) -> dict | None:
            async with semaphore:
                return await self.validate_one(config, session, check_ping=check_ping)

        tasks = [_validate_with_semaphore(cfg) for cfg in configs]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for outcome in outcomes:
            if isinstance(outcome, dict):
                results.append(outcome)
            elif isinstance(outcome, Exception):
                logger.warning("Validation error: {}", outcome)
        return results
