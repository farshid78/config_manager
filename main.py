# main.py — نقطه ورود اصلی برنامه
# این فایل ربات تلگرام، اسکرپر و ناشر را راه‌اندازی و مدیریت می‌کند

from __future__ import annotations  # پشتیبانی از type hints در نسخه‌های قدیمی‌تر پایتون

import asyncio  # عملیات ناهمزمان (async/await)
import json  # خواندن/نوشتن فایل‌های JSON
from pathlib import Path  # کار با مسیرهای فایل به صورت شیءگرا

import aiohttp  # کلاینت HTTP ناهمزمان
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # زمان‌بند وظایف ناهمزمان
from telegram.ext import (  # فریمورک ربات تلگرام
    Application,  # اپلیکیشن اصلی ربات
    CallbackQueryHandler,  # هندلر دکمه‌های شیشه‌ای (inline)
    CommandHandler,  # هندلر دستورات (/start, /health و غیره)
    MessageHandler,  # هندلر پیام‌های متنی و فایل
    filters,  # فیلترهای پیام (مثلاً فقط متن، فقط فایل)
)

from app.handlers.admin import handle_document, health_command  # هندلرهای ادمین
from app.handlers.router import callback_router, message_router  # مسیریاب پیام‌ها و دکمه‌ها
from app.handlers.user import start_command  # هندلر دستور /start
from constants import SCRAPER_PUBLISH_LIMIT  # حداکثر تعداد کانفیگ برای انتشار
from core.config import BASE_DIR, get_settings  # تنظیمات و مسیر پایه پروژه
from core.logger import get_logger, setup_logging  # سیستم لاگ‌گیری
from database import crud  # عملیات پایگاه داده (CRUD)
from database.session import close_db, get_session_factory, init_db  # مدیریت نشست دیتابیس
from processor.validator import ConfigValidator  # اعتبارسنجی کانفیگ‌ها
from publisher.broadcaster import Broadcaster  # انتشار کانفیگ در کانال تلگرام
from publisher.queue import PublishQueue  # صف ناهمزمان انتشار
from scraper.base import TelegramChannelScraper  # اسکرپر کانال‌های تلگرام

logger = get_logger()  # نمونه لاگر برای این ماژول


async def migrate_admins_json() -> None:
    """انتقال لیست ادمین‌ها از فایل JSON قدیمی به پایگاه داده."""
    legacy = BASE_DIR / "admins.json"
    if not legacy.exists():
        return
    try:
        with open(legacy, "r", encoding="utf-8") as f:
            ids = json.load(f)
        settings = get_settings()
        factory = get_session_factory()
        async with factory() as session:
            for uid in ids:
                if uid != settings.owner_id:
                    await crud.add_admin(session, int(uid), settings.owner_id)
        logger.info("Migrated {} admins from admins.json", len(ids))
    except Exception as exc:
        logger.warning("Admin migration skipped | {}", exc)


async def seed_default_sources() -> None:
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


async def scraper_job() -> None:
    """وظیفه دوره‌ای اسکرپر: جمع‌آوری → اعتبارسنجی → ذخیره → صف انتشار.

    این تابع توسط زمان‌بند (scheduler) در فواصل زمانی مشخص فراخوانی می‌شود.
    مراحل:
    1. بررسی فعال بودن اسکرپر در تنظیمات
    2. جمع‌آوری کانفیگ‌ها از کانال‌های منبع
    3. اعتبارسنجی دسته‌ای کانفیگ‌ها
    4. ذخیره کانفیگ‌های جدید در دیتابیس
    5. اضافه کردن کانفیگ‌ها به صف انتشار
    """
    settings = get_settings()
    if not settings.scraper_enabled:
        logger.debug("Scraper disabled in settings — skipped")
        return

    scraper = TelegramChannelScraper()
    validator = ConfigValidator()
    queue = PublishQueue.get()
    factory = get_session_factory()

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
                    new_count, new_configs = await crud.batch_save_configs(session, validated, source=source)

                # اضافه کردن فقط کانفیگ‌های جدیدِ واقعاً ذخیره‌شده به صف انتشار
                if new_count > 0:
                    for item in new_configs:
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


async def post_init(application: Application) -> None:
    """راه‌اندازی سرویس‌های پس‌زمینه بعد از مقداردهی اولیه ربات.

    مراحل:
    1. ایجاد جداول دیتابیس (اگر وجود نداشته باشند)
    2. انتقال ادمین‌ها از فایل JSON قدیمی
    3. شروع کار ناشر (broadcaster)
    4. راه‌اندازی زمان‌بند برای اسکرپر دوره‌ای
    5. اجرای اولین اسکرپ بلافاصله
    """
    await init_db()  # ایجاد جداول دیتابیس
    await migrate_admins_json()  # انتقال ادمین‌های قدیمی
    await seed_default_sources()  # ذخیره منابع پیش‌فرض اسکرپر در دیتابیس

    Broadcaster().start()  # شروع worker انتشار در پس‌زمینه

    settings = get_settings()  # دریافت تنظیمات
    scheduler = AsyncIOScheduler()  # ایجاد زمان‌بند ناهمزمان
    scheduler.add_job(  # افزودن وظیفه اسکرپر به زمان‌بند
        scraper_job,  # تابع وظیفه
        "interval",  # نوع زمان‌بندی: فواصل ثابت
        seconds=settings.scraper_interval,  # فاصله زمانی بین اجراها (ثانیه)
        id="scraper",  # شناسه یکتای وظیفه
        max_instances=1,  # حداکثر یک نمونه همزمان
        coalesce=True,  # ادغام وظایف از دست‌رفته
    )
    scheduler.start()  # شروع زمان‌بند
    application.bot_data["scheduler"] = scheduler  # ذخیره مرجع زمان‌بند در داده‌های ربات

    # اجرای اولین اسکرپ بلافاصله (بدون انتظار برای اولین فاصله زمانی)
    scraper_task = asyncio.create_task(scraper_job())
    application.bot_data["scraper_task"] = scraper_task
    logger.info("Background services started")  # لاگ شروع سرویس‌ها


async def post_shutdown(application: Application) -> None:
    """توقف تمیز سرویس‌ها هنگام خاموش شدن ربات.

    مراحل:
    1. توقف زمان‌بند
    2. کنسل کردن تسک اسکرپر
    3. توقف ناشر
    4. بستن اتصال دیتابیس
    """
    # 1. توقف زمان‌بند
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.shutdown(wait=False)

    # 2. کنسل کردن تسک اسکرپر
    scraper_task = application.bot_data.get("scraper_task")
    if scraper_task and not scraper_task.done():
        scraper_task.cancel()
        try:
            await asyncio.wait_for(scraper_task, timeout=5)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass

    # 3. توقف ناشر
    try:
        broadcaster = Broadcaster()
        await broadcaster.stop()
    except Exception as exc:
        logger.warning("Broadcaster stop error: {}", exc)

    # 4. بستن اتصال دیتابیس
    try:
        await close_db()
    except Exception as exc:
        logger.warning("DB close error: {}", exc)
    logger.info("Shutdown complete")


def build_application() -> Application:
    """ساخت و پیکربندی اپلیکیشن ربات تلگرام.

    - تنظیم توکن ربات
    - ثبت هندلرهای مختلف (دستورات، دکمه‌ها، پیام‌ها، فایل‌ها)
    - تنظیم توابع چرخه حیات (post_init, post_shutdown)
    """
    try:
        settings = get_settings()  # دریافت تنظیمات
        app = (  # ساخت اپلیکیشن
            Application.builder()
            .token(settings.bot_token)  # تنظیم توکن ربات
            .post_init(post_init)  # تابع اجرا پس از مقداردهی
            .post_shutdown(post_shutdown)  # تابع اجرا پیش از خاموشی
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

        # error handler برای جلوگیری از "No error handlers are registered"
        async def _error_handler(update, context):
            try:
                exc = context.error
                logger.error("Telegram error: {}", exc, exc_info=True)
            except Exception as _e:
                logger.error("Telegram error handler failed: {}", _e)

        app.add_error_handler(_error_handler)

        return app  # بازگرداندن اپلیکیشن آماده

    except Exception as e:
        error_msg = str(e)
        logger.error("Error building application: {}", error_msg)
        if "NetworkError" in error_msg or "ConnectionError" in error_msg or "ReadError" in error_msg:
            logger.error("Network error detected. Please check your internet connection.")
        raise  # خطا را مجدداً پرتاب می‌کنیم تا در تابع main مدیریت شود


def main() -> None:
    """نقطه ورود اصلی برنامه.

    1. راه‌اندازی سیستم لاگ‌گیری
    2. ساخت اپلیکیشن ربات
    3. شروع polling (دریافت پیام‌ها از سرور تلگرام)
    """
    setup_logging()  # پیکربندی لاگر
    logger.info("Starting {} ...", get_settings().project_name)  # لاگ شروع
    application = build_application()  # ساخت اپلیکیشن
    
    # تلاش برای شروع polling با مدیریت خطاهای شبکه
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info("Attempt {} to start polling...", retry_count + 1)
            application.run_polling(drop_pending_updates=True)  # شروع polling با نادیده گرفتن پیام‌های معلق
            break
        except Exception as e:
            error_msg = str(e)
            retry_count += 1
            
            if "ReadError" in error_msg or "NetworkError" in error_msg or "ConnectionError" in error_msg:
                logger.warning("Network error occurred (attempt {}/{}): {}", retry_count, max_retries, error_msg)
                if retry_count < max_retries:
                    logger.info("Retrying in 5 seconds...")
                    import time
                    time.sleep(5)  # انتظار 5 ثانیه قبل از تلاش مجدد
                else:
                    logger.error("Max retries reached. Exiting...")
                    break
            else:
                logger.error("Unexpected error: {}", error_msg)
                break


if __name__ == "__main__":  # اجرای مستقیم فایل
    main()  # فراخوانی تابع اصلی
