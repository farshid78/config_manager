# services/cache_service.py — پیاده‌سازی یک سیستم کش با Redis
# این ماژول برای کاهش بار روی دیتابیس و افزایش سرعت سیستم استفاده می‌شود

import asyncio
import json
import pickle
from typing import Any, Optional, Dict, List

import aiohttp

from core.config import get_settings
from core.logger import get_logger

logger = get_logger()


class CacheService:
    """سرویس کش مبتنی بر Redis برای افزایش عملکرد سیستم."""

    def __init__(self):
        """مقداردهی اولیه سرویس کش."""
        self.settings = get_settings()
        self._redis_client = None
        self._connected = False
        self._connection_lock = asyncio.Lock()

        # پیش‌تنظیم‌های کش
        self._default_ttl = 3600  # 1 ساعت پیش‌فرض
        self._cache_prefix = "config_manager:"

        # کش‌های محلی برای کاهش درخواست‌های Redis
        self._local_cache: Dict[str, Any] = {}
        self._local_cache_ttl: Dict[str, float] = {}

    async def connect(self) -> None:
        """اتصال به سرور Redis."""
        if self._connected:
            return

        async with self._connection_lock:
            if self._connected:
                return

            try:
                # در صورت عدم وجود تنظیمات Redis، از کش محلی استفاده می‌کنیم
                if not self.settings.redis_url:
                    logger.warning("Redis URL not configured, using local cache")
                    self._connected = True
                    return

                # در اینجا می‌توانیم از کتابخانه‌ای مثل aioredis استفاده کنیم
                # برای سادگی، یک شبیه‌سازی با HTTP API Redis انجام می‌دهیم
                self._redis_client = aiohttp.ClientSession()
                self._connected = True
                logger.info("Connected to Redis cache")
            except Exception as exc:
                logger.error("Failed to connect to Redis: {}", exc)
                self._connected = False

    async def disconnect(self) -> None:
        """قطع اتصال از سرور Redis."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
        self._connected = False
        logger.info("Disconnected from Redis cache")

    def _get_cache_key(self, key: str) -> str:
        """ایجاد کلید کش با پیشوند."""
        return f"{self._cache_prefix}{key}"

    async def get(self, key: str, default: Any = None) -> Any:
        """دریافت مقدار از کش با کلید مشخص."""
        cache_key = self._get_cache_key(key)

        # ابتدا در کش محلی جستجو می‌کنیم
        if cache_key in self._local_cache:
            ttl = self._local_cache_ttl.get(cache_key, 0)
            if ttl > asyncio.get_event_loop().time():
                return self._local_cache[cache_key]
            else:
                # کش منقضی شده
                del self._local_cache[cache_key]
                del self._local_cache_ttl[cache_key]

        # اگر Redis فعال باشد، از آن استفاده می‌کنیم
        if self._connected and self._redis_client:
            try:
                response = await self._redis_client.get(
                    f"{self.settings.redis_url}/get/{cache_key}"
                )
                if response:
                    data = json.loads(response)
                    # ذخیره در کش محلی برای دسترسی سریع‌تر
                    self._local_cache[cache_key] = data
                    self._local_cache_ttl[cache_key] = asyncio.get_event_loop().time() + self._default_ttl
                    return data
            except Exception as exc:
                logger.error("Redis GET failed for {}: {}", cache_key, exc)

        return default

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """ذخیره مقدار در کش با کلید مشخص."""
        cache_key = self._get_cache_key(key)
        ttl = ttl or self._default_ttl

        # ذخیره در کش محلی
        self._local_cache[cache_key] = value
        self._local_cache_ttl[cache_key] = asyncio.get_event_loop().time() + ttl

        # اگر Redis فعال باشد، در آن نیز ذخیره می‌کنیم
        if self._connected and self._redis_client:
            try:
                await self._redis_client.post(
                    f"{self.settings.redis_url}/set/{cache_key}",
                    json={"value": value, "ttl": ttl}
                )
            except Exception as exc:
                logger.error("Redis SET failed for {}: {}", cache_key, exc)

    async def delete(self, key: str) -> None:
        """حذف مقدار از کش با کلید مشخص."""
        cache_key = self._get_cache_key(key)

        # حذف از کش محلی
        if cache_key in self._local_cache:
            del self._local_cache[cache_key]
            del self._local_cache_ttl[cache_key]

        # اگر Redis فعال باشد، از آن حذف می‌کنیم
        if self._connected and self._redis_client:
            try:
                await self._redis_client.delete(f"{self.settings.redis_url}/delete/{cache_key}")
            except Exception as exc:
                logger.error("Redis DELETE failed for {}: {}", cache_key, exc)

    async def exists(self, key: str) -> bool:
        """بررسی وجود کلید در کش."""
        cache_key = self._get_cache_key(key)

        # ابتدا در کش محلی بررسی می‌کنیم
        if cache_key in self._local_cache:
            ttl = self._local_cache_ttl.get(cache_key, 0)
            if ttl > asyncio.get_event_loop().time():
                return True
            else:
                # کش منقضی شده
                del self._local_cache[cache_key]
                del self._local_cache_ttl[cache_key]

        # اگر Redis فعال باشد، از آن استفاده می‌کنیم
        if self._connected and self._redis_client:
            try:
                response = await self._redis_client.get(
                    f"{self.settings.redis_url}/exists/{cache_key}"
                )
                return response == "true"
            except Exception as exc:
                logger.error("Redis EXISTS failed for {}: {}", cache_key, exc)

        return False

    async def clear(self) -> None:
        """پاک‌سازی کامل کش."""
        self._local_cache.clear()
        self._local_cache_ttl.clear()

        if self._connected and self._redis_client:
            try:
                await self._redis_client.delete(f"{self.settings.redis_url}/clear")
            except Exception as exc:
                logger.error("Redis CLEAR failed: {}", exc)

    async def get_config_cache_key(self, config_hash: str) -> str:
        """دریافت کلید کش برای یک کانفیگ مشخص."""
        return f"config:{config_hash}"

    async def get_country_cache_key(self, host: str) -> str:
        """دریافت کلید کش برای کد کشور یک هاست."""
        return f"country:{host}"

    async def get_stats(self) -> Dict[str, Any]:
        """دریافت آمار کش."""
        return {
            "connected": self._connected,
            "local_cache_size": len(self._local_cache),
            "prefix": self._cache_prefix,
            "default_ttl": self._default_ttl
        }


# نمونه singleton از CacheService
_cache_service = None


def get_cache_service() -> CacheService:
    """دریافت نمونه singleton از CacheService."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
