# services/scraper_service.py — سرویس مستقل اسکرپر
# این سرویس مسئولیت جمع‌آوری و اعتبارسنجی کانفیگ‌ها را دارد

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from constants import SCRAPER_PUBLISH_LIMIT
from core.config import get_settings
from core.logger import get_logger
from database import crud
from database.session import get_session_factory
from processor.validator import ConfigValidator
from publisher.queue import PublishQueue
from scraper.base import TelegramChannelScraper
from scraper.sources import SUBSCRIPTION_SOURCES
from scraper.subscription import SubscriptionScraper
from services.cache_service import get_cache_service
from services.error_handler import get_error_handler, ErrorType
from services.message_queue import get_message_queue, MessageType

logger = get_logger()

# نمونه‌های singleton
_cache_service = get_cache_service()
_error_handler = get_error_handler()
_message_queue = get_message_queue()


class ScraperService:
    """سرویس مستقل اسکرپر.

    این سرویس مسئولیت‌های زیر را بر عهده دارد:
    - جمع‌آوری کانفیگ‌ها از منابع مختلف
    - اعتبارسنجی کانفیگ‌ها
    - ذخیره کانفیگ‌ها در دیتابیس
    - ارسال کانفیگ‌های جدید به صف انتشار
    """

    def __init__(self):
        """مقداردهی اولیه سرویس اسکرپر."""
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.scraper = TelegramChannelScraper()
        self.validator = ConfigValidator()
        self.queue = PublishQueue.get()
        self._task = None

    async def start(self) -> None:
        """راه‌اندازی سرویس اسکرپر."""
        logger.info("Starting scraper service ...")

        # اتصال به سیستم‌های پایه
        await _cache_service.connect()

        # اشتراک در پیام‌های مربوط به نشر
        await _message_queue.subscribe(MessageType.CONFIG_VALIDATED, self._on_config_validated)

        # افزودن وظیفه اسکرپر به زمان‌بند
        self.scheduler.add_job(
            self._scraper_job,
            "interval",
            seconds=self.settings.scraper_interval,
            id="scraper",
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()

        # اجرای اولین اسکرپ بلافاصله (بدون انتظار برای اولین فاصله زمانی)
        self._task = asyncio.create_task(self._scraper_job())
        logger.info("Scraper service started")

    async def stop(self) -> None:
        """توقف سرویس اسکرپر."""
        if self.scheduler:
            self.scheduler.shutdown(wait=False)

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # لغو اشتراک از پیام‌ها
        await _message_queue.unsubscribe(MessageType.CONFIG_VALIDATED, self._on_config_validated)

        # قطع اتصال از سیستم‌ها
        await _cache_service.disconnect()

        logger.info("Scraper service stopped")

    async def _scraper_job(self) -> None:
        """وظیفه دوره‌ای اسکرپر: جمع‌آوری → اعتبارسنجی → ذخیره → صف انتشار.

        این تابع توسط زمان‌بند (scheduler) در فواصل زمانی مشخص فراخوانی می‌شود.
        مراحل:
        1. بررسی فعال بودن اسکرپر در تنظیمات
        2. جمع‌آوری کانفیگ‌ها از کانال‌های منبع
        3. اعتبارسنجی دسته‌ای کانفیگ‌ها
        4. ذخیره کانفیگ‌های جدید در دیتابیس
        5. ارسال کانفیگ‌های جدید به صف انتشار از طریق پیام‌ها
        """
        if not self.settings.scraper_enabled:
            logger.debug("Scraper disabled in settings — skipped")
            return

        # استفاده از Circuit Breaker برای جلوگیری از خطاهای مداوم
        circuit_breaker = _error_handler.get_circuit_breaker("scraper_network", failure_threshold=5)

        # استفاده از Retry Handler برای تلاش مجدد در صورت خطا
        retry_handler = _error_handler.get_retry_handler("scraper_retries", max_retries=3)

        http_session: aiohttp.ClientSession | None = None
        try:
            # ایجاد نشست HTTP با استفاده از Retry Handler
            http_session = await retry_handler.execute(
                aiohttp.ClientSession
            )

            # اسکرپ تمام منابع با استفاده از Circuit Breaker
            all_sources = await circuit_breaker.call(
                self.scraper.scrape_all, 
                http_session
            )

            total_scraped = sum(len(c) for c in all_sources.values())
            logger.info("Scrape complete | total_configs={}", total_scraped)

            for source, configs in all_sources.items():
                try:
                    if not configs:
                        continue

                    # محدودیت تعداد کانفیگ برای سرعت بیشتر
                    limited = configs[:SCRAPER_PUBLISH_LIMIT]
                    logger.info("Validating {} | configs={}", source, len(limited))

                    # اعتبارسنجی دسته‌ای (بدون ping برای سرعت بیشتر)
                    validated = await self.validator.validate_batch(limited, http_session, check_ping=False)
                    logger.info("Validated {} | valid={}", source, len(validated))

                    if not validated:
                        continue

                    # ذخیره دسته‌ی کانفیگ‌ها با استفاده از Retry Handler
                    async with get_session_factory() as session:
                        new_count, new_configs = await retry_handler.execute(
                            crud.batch_save_configs,
                            session,
                            validated,
                            source=source,
                        )

                    # اگر کانفیگ جدید وجود داشت، از طریق پیام به ناشر ارسال شود
                    if new_count > 0:
                        for item in new_configs:
                            # ذخیره کش برای کانفیگ‌های جدید
                            config_cache_key = await _cache_service.get_config_cache_key(item["config_hash"])
                            await _cache_service.set(
                                config_cache_key,
                                item,
                                ttl=3600  # 1 ساعت
                            )

                            # ارسال پیام برای نشر
                            await _message_queue.publish(
                                MessageType.CONFIG_VALIDATED,
                                {
                                    "config": item["watermarked_config"],
                                    "country_code": item["country_code"],
                                    "config_hash": item["config_hash"],
                                    "protocol": item["protocol"],
                                    "host": item["host"],
                                },
                                "scraper_service",
                            )

                        logger.info("New configs from {}: {}", source, new_count)
                    else:
                        logger.debug("Duplicate configs from {} — skipped", source)

                except Exception as exc:
                    # ثبت خطا در سیستم مدیریت خطا
                    await _error_handler.log_error(
                        ErrorType.SCRAPER_ERROR,
                        f"Error processing source {source}",
                        str(exc),
                        "scraper_service"
                    )
                    logger.error("Error processing source {}: {}", source, exc)

        except asyncio.CancelledError:
            logger.info("Scraper job cancelled — shutting down")
        except Exception as exc:
            # ثبت خطا در سیستم مدیریت خطا
            await _error_handler.log_error(
                ErrorType.SCRAPER_ERROR,
                "Scraper job failed",
                str(exc),
                "scraper_service"
            )
            logger.error("Scraper job failed: {}", exc)
        else:
            logger.info("Scraper job completed successfully")
        finally:
            if http_session and not http_session.closed:
                await http_session.close()

    async def _on_config_validated(self, message) -> None:
        """مدیریت پیام‌های مربوط به کانفیگ‌های اعتبارسنجی شده."""
        # در حال حاضر اسکرپر فقط پیام‌ها را ارسال می‌کند و دریافت نمی‌کند
        # این متد برای آینده预留 شده است
        pass

    async def scrape_source_manually(self, source_name: str) -> Dict[str, List[str]]:
        """اسکرپ دستی یک منبع خاص.

        Args:
            source_name: نام منبع برای اسکرپ دستی

        Returns:
            دیکشنری {نام_منبع: [لیست_کانفیگ‌ها]}
        """
        http_session: aiohttp.ClientSession | None = None
        try:
            http_session = aiohttp.ClientSession()

            # دریافت منبع از دیتابیس
            factory = get_session_factory()
            async with factory() as session:
                source = await crud.get_scraper_source_by_name(session, source_name)
                if not source:
                    logger.error("Source not found: {}", source_name)
                    return {}

                # اسکرپ منبع
                if source.source_type == "telegram":
                    configs = await self.scraper.scrape_source(source.url, http_session)
                elif source.source_type == "subscription":
                    sub_scraper = SubscriptionScraper()
                    from scraper.sources import Source
                    source_obj = Source(name=source.name, url=source.url, source_type=source.source_type)
                    configs = await sub_scraper.scrape_subscription(source_obj, http_session)
                else:
                    logger.warning("Unknown source type: {} — skipped", source.source_type)
                    return {}

                # به‌روزرسانی آمار در دیتابیس
                await crud.update_scraper_source_stats(session, source.url, len(configs))

                logger.info("Manual scrape {} ({}) | configs={}", source.name, source.source_type, len(configs))
                return {source.name: configs}

        except Exception as exc:
            logger.error("Manual scrape failed for {}: {}", source_name, exc)
            return {}
        finally:
            if http_session and not http_session.closed:
                await http_session.close()

    async def get_stats(self) -> Dict[str, int]:
        """دریافت آمار اسکرپر.

        Returns:
            دیکشنری با آمارهای اسکرپر
        """
        try:
            factory = get_session_factory()
            async with factory() as session:
                total_configs = await crud.count_processed_configs(session)
                total_sources = await crud.count_scraper_sources(session)
                active_sources = await crud.count_active_scraper_sources(session)

                return {
                    "total_configs": total_configs,
                    "total_sources": total_sources,
                    "active_sources": active_sources,
                }
        except Exception as exc:
            logger.error("Failed to get scraper stats: {}", exc)
            return {}

    async def get_sources(self) -> List[Dict]:
        """دریافت لیست منابع اسکرپر.

        Returns:
            لیست دیکشنری‌های حاوی اطلاعات منابع
        """
        try:
            factory = get_session_factory()
            async with factory() as session:
                sources = await crud.list_scraper_sources(session)
                return [
                    {
                        "id": source.id,
                        "name": source.name,
                        "url": source.url,
                        "source_type": source.source_type,
                        "is_active": source.is_active,
                        "last_scraped": source.last_scraped,
                        "last_config_count": source.last_config_count,
                        "created_at": source.created_at,
                    }
                    for source in sources
                ]
        except Exception as exc:
            logger.error("Failed to get scraper sources: {}", exc)
            return []

    async def add_source(self, name: str, url: str, source_type: str) -> str:
        """افزودن منبع جدید به اسکرپر.

        Args:
            name: نام منبع
            url: آدرس منبع
            source_type: نوع منبع (telegram یا subscription)

        Returns:
            وضعیت افزودن ("added", "duplicate_url", "duplicate_name")
        """
        try:
            factory = get_session_factory()
            async with factory() as session:
                result = await crud.add_scraper_source(
                    session, name=name, url=url, source_type=source_type
                )

                if result == "added":
                    logger.info("Added new source: {} ({})", name, source_type)
                else:
                    logger.warning("Source add result: {}", result)

                return result
        except Exception as exc:
            logger.error("Failed to add source {}: {}", name, exc)
            return "error"

    async def remove_source(self, source_id: int) -> bool:
        """حذف منبع از اسکرپر.

        Args:
            source_id: شناسه منبع

        Returns:
            آیا حذف با موفقیت انجام شد
        """
        try:
            factory = get_session_factory()
            async with factory() as session:
                result = await crud.remove_scraper_source(session, source_id)

                if result:
                    logger.info("Removed source with ID: {}", source_id)
                else:
                    logger.warning("Source not found with ID: {}", source_id)

                return result
        except Exception as exc:
            logger.error("Failed to remove source {}: {}", source_id, exc)
            return False

    async def toggle_source(self, source_id: int) -> bool:
        """تغییر وضعیت فعال/غیرفعال یک منبع.

        Args:
            source_id: شناسه منبع

        Returns:
            آیا تغییر با موفقیت انجام شد
        """
        try:
            factory = get_session_factory()
            async with factory() as session:
                source = await crud.get_scraper_source(session, source_id)
                if not source:
                    logger.warning("Source not found with ID: {}", source_id)
                    return False

                new_status = not source.is_active
                await crud.update_scraper_source_status(session, source_id, new_status)

                logger.info("Toggled source {} to {}", source_id, "active" if new_status else "inactive")
                return True
        except Exception as exc:
            logger.error("Failed to toggle source {}: {}", source_id, exc)
            return False

    async def get_latest_configs(self, limit: int = 50) -> List[Dict]:
        """دریافت جدیدترین کانفیگ‌ها.

        Args:
            limit: حداکثر تعداد کانفیگ‌ها

        Returns:
            لیست دیکشنری‌های حاوی اطلاعات کانفیگ‌ها
        """
        try:
            factory = get_session_factory()
            async with factory() as session:
                configs = await crud.get_latest_configs(session, limit=limit)
                return [
                    {
                        "id": config.id,
                        "country_code": config.country_code,
                        "protocol": config.protocol,
                        "host": config.host,
                        "source": config.source,
                        "is_valid": config.is_valid,
                        "created_at": config.created_at,
                    }
                    for config in configs
                ]
        except Exception as exc:
            logger.error("Failed to get latest configs: {}", exc)
            return []
