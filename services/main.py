# services/main.py — نقطه ورود اصلی سرویس‌های مستقل
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
    """مدیر سرویس‌های برنامه با معماری مایکروسرویس.

    این کلاس مسئولیت راه‌اندازی، مدیریت و توقف سرویس‌ها را بر عهده دارد.
    سرویس‌ها به صورت مستقل اجرا می‌شوند و از طریق Message Queue با یکدیگر ارتباط برقرار می‌کنند.
    """

    def __init__(self, service_type: Optional[str] = None):
        """مقداردهی اولیه مدیر سرویس‌ها.

        Args:
            service_type: نوع سرویس که مشخص می‌کند کدام سرویس‌ها باید اجرا شوند
                         (None: همه سرویس‌ها, "bot": فقط ربات, "scraper": فقط اسکرپر, "publisher": فقط نشر)
        """
        self.settings = get_settings()
        self.service_type = service_type
        self.services: List[dict] = []
        self._running = False

        # مقداردهی اولیه سرویس‌های پایه
        self.cache_service = get_cache_service()
        self.error_handler = get_error_handler()
        self.message_queue = get_message_queue()

    async def start_bot(self) -> None:
        """راه‌اندازی سرویس ربات به صورت مستقل."""
        logger.info("Starting Bot service ...")

        try:
            # اتصال به Redis
            await self.cache_service.connect()

            # راه‌اندازی سرویس ربات
            bot_service = BotService()
            await bot_service.start()
            self.services.append({"name": "Bot", "service": bot_service})
            logger.info("Bot service started successfully")

            # منتظر ماندن برای سیگنال خروج
            while True:
                await asyncio.sleep(1)

        except Exception as exc:
            logger.error("Failed to start Bot service: {}", exc)
            await self.stop_bot()
            sys.exit(1)

    async def start_scraper(self) -> None:
        """راه‌اندازی سرویس اسکرپر به صورت مستقل."""
        logger.info("Starting Scraper service ...")

        try:
            # اتصال به Redis
            await self.cache_service.connect()

            # راه‌اندازی سرویس اسکرپر
            scraper_service = ScraperService()
            await scraper_service.start()
            self.services.append({"name": "Scraper", "service": scraper_service})
            logger.info("Scraper service started successfully")

            # منتظر ماندن برای سیگنال خروج
            while True:
                await asyncio.sleep(1)

        except Exception as exc:
            logger.error("Failed to start Scraper service: {}", exc)
            await self.stop_scraper()
            sys.exit(1)

    async def start_publisher(self) -> None:
        """راه‌اندازی سرویس نشر به صورت مستقل."""
        logger.info("Starting Publisher service ...")

        try:
            # اتصال به Redis
            await self.cache_service.connect()

            # راه‌اندازی سرویس نشر
            publisher_service = PublisherService()
            await publisher_service.start()
            self.services.append({"name": "Publisher", "service": publisher_service})
            logger.info("Publisher service started successfully")

            # منتظر ماندن برای سیگنال خروج
            while True:
                await asyncio.sleep(1)

        except Exception as exc:
            logger.error("Failed to start Publisher service: {}", exc)
            await self.stop_publisher()
            sys.exit(1)

    async def start_all(self) -> None:
        """راه‌اندازی تمام سرویس‌ها."""
        logger.info("Starting all services ...")

        try:
            # اتصال به Redis
            await self.cache_service.connect()

            # راه‌اندازی سرویس‌ها به ترتیب
            services_to_start = []

            if self.service_type is None or self.service_type == "scraper":
                services_to_start.append({"name": "Scraper", "service": ScraperService()})

            if self.service_type is None or self.service_type == "publisher":
                services_to_start.append({"name": "Publisher", "service": PublisherService()})

            if self.service_type is None or self.service_type == "bot":
                services_to_start.append({"name": "Bot", "service": BotService()})

            for service_info in services_to_start:
                service_name = service_info["name"]
                service = service_info["service"]

                try:
                    logger.info("Starting {} service ...", service_name)
                    await service.start()
                    self.services.append(service_info)
                    logger.info("{} service started successfully", service_name)
                except Exception as exc:
                    logger.error("Failed to start {} service: {}", service_name, exc)
                    await self.stop_all()
                    sys.exit(1)

            logger.info("All services started successfully")

            # منتظر ماندن برای سیگنال خروج
            while True:
                await asyncio.sleep(1)

        except Exception as exc:
            logger.error("Failed to start services: {}", exc)
            await self.stop_all()
            sys.exit(1)

    async def stop_bot(self) -> None:
        """توقف سرویس ربات."""
        logger.info("Stopping Bot service ...")

        # توقف سرویس‌ها به ترتیب معکوس
        for service_info in reversed(self.services):
            if service_info["name"] == "Bot":
                service = service_info["service"]
                try:
                    await service.stop()
                    logger.info("Bot service stopped successfully")
                except Exception as exc:
                    logger.error("Error stopping Bot service: {}", exc)
                break

        # قطع اتصال از Redis
        await self.cache_service.disconnect()

        logger.info("Bot service shutdown complete")

    async def stop_scraper(self) -> None:
        """توقف سرویس اسکرپر."""
        logger.info("Stopping Scraper service ...")

        # توقف سرویس‌ها به ترتیب معکوس
        for service_info in reversed(self.services):
            if service_info["name"] == "Scraper":
                service = service_info["service"]
                try:
                    await service.stop()
                    logger.info("Scraper service stopped successfully")
                except Exception as exc:
                    logger.error("Error stopping Scraper service: {}", exc)
                break

        # قطع اتصال از Redis
        await self.cache_service.disconnect()

        logger.info("Scraper service shutdown complete")

    async def stop_publisher(self) -> None:
        """توقف سرویس نشر."""
        logger.info("Stopping Publisher service ...")

        # توقف سرویس‌ها به ترتیب معکوس
        for service_info in reversed(self.services):
            if service_info["name"] == "Publisher":
                service = service_info["service"]
                try:
                    await service.stop()
                    logger.info("Publisher service stopped successfully")
                except Exception as exc:
                    logger.error("Error stopping Publisher service: {}", exc)
                break

        # قطع اتصال از Redis
        await self.cache_service.disconnect()

        logger.info("Publisher service shutdown complete")

    async def stop_all(self) -> None:
        """توقف تمام سرویس‌ها."""
        logger.info("Stopping all services ...")

        # توقف سرویس‌ها به ترتیب معکوس
        for service_info in reversed(self.services):
            service_name = service_info["name"]
            service = service_info["service"]

            try:
                logger.info("Stopping {} service ...", service_name)
                await service.stop()
                logger.info("{} service stopped successfully", service_name)
            except Exception as exc:
                logger.error("Error stopping {} service: {}", service_name, exc)

        # قطع اتصال از Redis
        await self.cache_service.disconnect()

        logger.info("All services stopped")

    def setup_signal_handlers(self) -> None:
        """تنظیم هندلرهای سیگنال برای توقف به موقع سرویس‌ها."""
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self._handle_signal)

    def _handle_signal(self, signum, frame) -> None:
        """مدیریت سیگنال‌های توقف برنامه."""
        logger.info("Received signal {} — shutting down ...", signum)
        self._running = False
        asyncio.create_task(self.stop_all())
        sys.exit(0)


async def main() -> None:
    """نقطه ورود اصلی برنامه."""
    setup_logging()
    logger.info("Starting {} services ...", get_settings().project_name)

    # تعیین نوع سرویس از متغیر محیطی
    service_type = os.environ.get("SERVICE_TYPE", None)

    manager = ServiceManager(service_type)
    manager.setup_signal_handlers()

    try:
        if service_type == "bot":
            await manager.start_bot()
        elif service_type == "scraper":
            await manager.start_scraper()
        elif service_type == "publisher":
            await manager.start_publisher()
        else:
            await manager.start_all()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt — shutting down ...")
    except Exception as exc:
        logger.error("Unexpected error: {}", exc)
    finally:
        await manager.stop_all()


if __name__ == "__main__":
    asyncio.run(main())
