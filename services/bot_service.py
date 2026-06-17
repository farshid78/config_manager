# services/bot_service.py — سرویس مستقل ربات تلگرام
# این سرویس مسئولیت‌های ربات را مدیریت می‌کند

import asyncio
from pathlib import Path

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.handlers.admin import handle_document, health_command
from app.handlers.router import callback_router, message_router
from app.handlers.user import start_command
from core.config import get_settings
from core.logger import get_logger, setup_logging
from database import crud
from database.session import close_db, get_session_factory, init_db

logger = get_logger()


class BotService:
    """سرویس مستقل ربات تلگرام.

    این سرویس مسئولیت‌های زیر را بر عهده دارد:
    - راه‌اندازی ربات
    - مدیریت هندلرها
    - مدیریت چرخه حیات ربات
    """

    def __init__(self):
        """مقداردهی اولیه سرویس ربات."""
        self.settings = get_settings()
        self.app: Application | None = None
        self.scheduler = None
        self.scraper_task = None

    def build_application(self) -> Application:
        """ساخت و پیکربندی اپلیکیشن ربات تلگرام.

        - تنظیم توکن ربات
        - ثبت هندلرهای مختلف (دستورات، دکمه‌ها، پیام‌ها، فایل‌ها)
        - تنظیم توابع چرخه حیات (post_init, post_shutdown)
        """
        app = (
            Application.builder()
            .token(self.settings.bot_token)
            .build()
        )

        # ثبت هندلر دستور /start
        app.add_handler(CommandHandler("start", start_command))
        # ثبت هندلر دستور /health (بررسی سلامت سیستم)
        app.add_handler(CommandHandler("health", health_command))
        # ثبت هندلر دکمه‌های شیشه‌ای (callback queries)
        app.add_handler(CallbackQueryHandler(callback_router))
        # ثبت هندلر پیام‌های متنی (غیر دستورات)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
        # ثبت هندلر فایل‌های ارسالی (آپلود فایل Clean IP)
        app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

        return app

    async def post_init(self, application: Application) -> None:
        """راه‌اندازی سرویس‌های پس‌زمینه بعد از مقداردهی اولیه ربات.

        مراحل:
        1. ایجاد جداول دیتابیس (اگر وجود نداشته باشند)
        2. انتقال ادمین‌ها از فایل JSON قدیمی
        3. شروع کار ناشر (broadcaster)
        4. راه‌اندازی زمان‌بند برای اسکرپر دوره‌ای
        5. اجرای اولین اسکرپ بلافاصله
        """
        await init_db()  # ایجاد جداول دیتابیس
        await self._migrate_admins_json()  # انتقال ادمین‌های قدیمی
        await self._seed_default_sources()  # ذخیره منابع پیش‌فرض اسکرپر در دیتابیس

        # ذخیره مرجع زمان‌بند در داده‌های ربات
        application.bot_data["scheduler"] = self.scheduler

        # اجرای اولین اسکرپ بلافاصله (بدون انتظار برای اولین فاصله زمانی)
        self.scraper_task = asyncio.create_task(self._scraper_job())
        application.bot_data["scraper_task"] = self.scraper_task
        logger.info("Bot service initialized")

    async def post_shutdown(self, application: Application) -> None:
        """توقف تمیز سرویس‌ها هنگام خاموش شدن ربات.

        مراحل:
        1. توقف زمان‌بند
        2. کنسل کردن تسک اسکرپر
        3. توقف ناشر
        4. بستن اتصال دیتابیس
        """
        # 1. توقف زمان‌بند
        if self.scheduler:
            self.scheduler.shutdown(wait=False)

        # 2. کنسل کردن تسک اسکرپر
        if self.scraper_task and not self.scraper_task.done():
            self.scraper_task.cancel()
            try:
                await asyncio.wait_for(self.scraper_task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        # 4. بستن اتصال دیتابیس
        try:
            await close_db()
        except Exception as exc:
            logger.warning("DB close error: {}", exc)
        logger.info("Bot service shutdown complete")

    async def _migrate_admins_json(self) -> None:
        """انتقال لیست ادمین‌ها از فایل JSON قدیمی به پایگاه داده."""
        from pathlib import Path

        legacy = Path("admins.json")
        if not legacy.exists():
            return
        try:
            import json
            with open(legacy, "r", encoding="utf-8") as f:
                ids = json.load(f)
            factory = get_session_factory()
            async with factory() as session:
                for uid in ids:
                    if uid != self.settings.owner_id:
                        await crud.add_admin(session, int(uid), self.settings.owner_id)
            logger.info("Migrated {} admins from admins.json", len(ids))
        except Exception as exc:
            logger.warning("Admin migration skipped | {}", exc)

    async def _seed_default_sources(self) -> None:
        """ذخیره منابع پیش‌فرض اسکرپر در دیتابیس (اگر دیتابیس خالی باشد).

        اگر جدول scraper_sources خالی باشد، منابع پیش‌فرض از فایل sources.py
        به دیتابیس اضافه می‌شوند تا از طریق پنل مدیریت قابل مدیریت باشند.
        """
        from scraper.sources import TELEGRAM_SOURCES, SUBSCRIPTION_SOURCES

        factory = get_session_factory()
        try:
            async with factory() as session:
                existing = await crud.list_scraper_sources(session)
                if existing:
                    logger.debug("Scraper sources already in DB ({})", len(existing))
                    return

                # افزودن منابع تلگرام
                tg_added = 0
                for src in TELEGRAM_SOURCES:
                    result = await crud.add_scraper_source(
                        session, name=src.name, url=src.url, source_type=src.source_type
                    )
                    if result == "added":
                        tg_added += 1

                # افزودن منابع اشتراک
                sub_added = 0
                for src in SUBSCRIPTION_SOURCES:
                    result = await crud.add_scraper_source(
                        session, name=src.name, url=src.url, source_type=src.source_type
                    )
                    if result == "added":
                        sub_added += 1

            total = tg_added + sub_added
            logger.info("Default scraper sources seeded (telegram: {}, subscription: {}, total: {})", tg_added, sub_added, total)
        except Exception as exc:
            logger.warning("Default sources seed failed | {}", exc)

    async def _scraper_job(self) -> None:
        """وظیفه دوره‌ای اسکرپر: جمع‌آوری → اعتبارسنجی → ذخیره → صف انتشار.

        این تابع توسط زمان‌بند (scheduler) در فواصل زمانی مشخص فراخوانی می‌شود.
        مراحل:
        1. بررسی فعال بودن اسکرپر در تنظیمات
        2. جمع‌آوری کانفیگ‌ها از کانال‌های منبع
        3. اعتبارسنجی دسته‌ای کانفیگ‌ها
        4. ذخیره کانفیگ‌های جدید در دیتابیس
        5. اضافه کردن کانفیگ‌ها به صف انتشار

        نکته: این تابع دیگر مسئولیت انتشار مستقیم را ندارد و فقط به صف نشر ارسال می‌کند.
        """
        from constants import SCRAPER_PUBLISH_LIMIT
        from scraper.base import TelegramChannelScraper
        from processor.validator import ConfigValidator
        from publisher.queue import PublishQueue

        if not self.settings.scraper_enabled:
            logger.debug("Scraper disabled in settings — skipped")
            return

        scraper = TelegramChannelScraper()
        validator = ConfigValidator()
        queue = PublishQueue.get()
        factory = get_session_factory()

        import aiohttp
        http_session: aiohttp.ClientSession | None = None
        try:
            http_session = aiohttp.ClientSession()
            all_sources = await scraper.scrape_all(http_session)
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
                    validated = await validator.validate_batch(limited, http_session, check_ping=False)
                    logger.info("Validated {} | valid={}", source, len(validated))

                    if not validated:
                        continue

                    # ذخیره دسته‌ای — یک کوئری + یک commit به جای N کوئری + N commit
                    async with factory() as session:
                        new_count = await crud.batch_save_configs(session, validated, source=source)

                    # اضافه کردن فقط کانفیگ‌های جدید به صف انتشار
                    if new_count > 0:
                        # فقط new_count کانفیگ جدید به صف اضافه شود
                        for item in validated[:new_count]:
                            await queue.put(item["watermarked_config"], item["country_code"])
                        logger.info("New configs from {}: {}", source, new_count)
                    else:
                        logger.debug("Duplicate configs from {} — skipped", source)
                except Exception as exc:
                    logger.error("Error processing source {}: {}", source, exc)

        except asyncio.CancelledError:
            logger.info("Scraper job cancelled — shutting down")
        except Exception as exc:
            logger.error("Scraper job failed: {}", exc)
        else:
            logger.info("Scraper job completed successfully")
        finally:
            if http_session and not http_session.closed:
                await http_session.close()

    async def start(self) -> None:
        """راه‌اندازی سرویس ربات."""
        setup_logging()  # پیکربندی لاگر
        logger.info("Starting {} bot service ...", self.settings.project_name)

        self.app = self.build_application()

        # تنظیم توابع چرخه حیات
        self.app.post_init_hook = self.post_init
        self.app.post_shutdown_hook = self.post_shutdown

        # شروع polling (دریافت پیام‌ها از سرور تلگرام)
        await self.app.run_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        """توقف سرویس ربات."""
        if self.app:
            await self.app.stop()
