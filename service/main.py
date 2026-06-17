# service/main.py — نقطه ورود اصلی سرویس‌های مستقل
# این فایل سرویس‌های ربات، اسکرپر و نشر را راه‌اندازی و مدیریت می‌کند

import asyncio
import os
import signal
import sys
from typing import List, Optional

from core.config import get_settings
from core.logger import get_logger, setup_logging
from services import BotService, PublisherService, ScraperService
from services.cache_service import get_cache_service
from services.error_handler import get_error_handler, ErrorType
from services.message_queue import get_message_queue, MessageType

logger = get_logger()


class ServiceManager:
    """مدیریت سرویس‌های مختلف سیستم."""

    def __init__(self):
        """مقداردهی اولیه مدیر سرویس‌ها."""
        self.settings = get_settings()
        self.cache_service = get_cache_service()
        self.error_handler = get_error_handler()
        self.message_queue = get_message_queue()
        self.services: List[BotService | PublisherService | ScraperService] = []

        # ثبت هندلرهای خطا
        self._setup_error_handlers()

        # ثبت سیگنال‌های سیستم
        self._setup_signal_handlers()

    def _setup_error_handlers(self):
        """تنظیم هندلرهای خطا."""
        async def handle_database_error(error: Exception, context: Optional[dict] = None):
            """هندلر خطاهای دیتابیس."""
            logger.error("Database error occurred", exc_info=error)
            # در صورت نیاز، می‌توان اقدامات خاصی انجام داد

        async def handle_network_error(error: Exception, context: Optional[dict] = None):
            """هندلر خطاهای شبکه."""
            logger.error("Network error occurred", exc_info=error)
            # در صورت نیاز، می‌توان اقدامات خاصی انجام داد

        async def handle_publishing_error(error: Exception, context: Optional[dict] = None):
            """هندلر خطاهای انتشار."""
            logger.error("Publishing error occurred", exc_info=error)
            # در صورت نیاز، می‌توان اقدامات خاصی انجام داد

        self.error_handler.register_handler(ErrorType.DATABASE, handle_database_error)
        self.error_handler.register_handler(ErrorType.NETWORK, handle_network_error)
        self.error_handler.register_handler(ErrorType.PUBLISHING, handle_publishing_error)

    def _setup_signal_handlers(self):
        """تنظیم هندلرهای سیگنال سیستم."""
        def signal_handler(sig, frame):
            """هندلر سیگنال‌های خروج."""
            logger.info("Received signal {}, shutting down...".format(sig))
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def initialize(self):
        """مقداردهی اولیه سرویس‌ها."""
        logger.info("Initializing services...")

        # اتصال به کش
        await self.cache_service.connect()

        # راه‌اندازی صف پیام‌ها
        message_task = self.message_queue.start_processing()

        # ایجاد سرویس‌ها
        self.services = [
            BotService(),
            PublisherService(),
            ScraperService(),
        ]

        # راه‌اندازی سرویس‌ها
        for service in self.services:
            await service.initialize()

        logger.info("All services initialized")

    async def run(self):
        """اجرای سرویس‌ها."""
        logger.info("Running services...")

        try:
            # اجرای سرویس‌ها
            tasks = []
            for service in self.services:
                task = asyncio.create_task(service.run())
                tasks.append(task)

            # منتظر ماندن تا تمام تسک‌ها تمام شوند
            await asyncio.gather(*tasks)

        except Exception as exc:
            logger.error("Service error occurred", exc_info=exc)
            await self.error_handler.handle_error(ErrorType.UNKNOWN, exc)
        finally:
            await self.shutdown()

    async def shutdown(self):
        """خاتمه سرویس‌ها."""
        logger.info("Shutting down services...")

        # توقف سرویس‌ها
        for service in self.services:
            try:
                await service.stop()
            except Exception as exc:
                logger.error("Error stopping service", exc_info=exc)

        # قطع اتصال از کش
        await self.cache_service.disconnect()

        logger.info("All services stopped")


async def main():
    """نقطه ورود اصلی برنامه."""
    # تنظیم لاگ‌ها
    setup_logging()

    # ایجاد و اجرای مدیر سرویس‌ها
    manager = ServiceManager()
    await manager.initialize()
    await manager.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as exc:
        logger.error("Fatal error", exc_info=exc)
        sys.exit(1)
