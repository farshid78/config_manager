# main.py — نقطه ورود اصلی (bot + scraper + publisher)

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
from constants import SCRAPER_PUBLISH_LIMIT
from core.config import BASE_DIR, get_settings
from core.logger import get_logger, setup_logging
from database import crud
from database.session import close_db, get_session_factory, init_db
from processor.validator import ConfigValidator
from publisher.broadcaster import Broadcaster
from publisher.queue import PublishQueue
from scraper.base import TelegramChannelScraper

logger = get_logger()


async def migrate_admins_json() -> None:
    """انتقال admins.json قدیمی به DB."""
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


async def scraper_job() -> None:
    """Job دوره‌ای scrape → validate → DB → queue."""
    from app.handlers.admin import scraper_is_enabled

    settings = get_settings()
    if not settings.scraper_enabled:
        logger.debug("Scraper disabled in config — skip")
        return

    scraper = TelegramChannelScraper()
    validator = ConfigValidator()
    queue = PublishQueue.get()
    factory = get_session_factory()

    try:
        async with aiohttp.ClientSession() as http_session:
            all_sources = await scraper.scrape_all(http_session)

            for source, configs in all_sources.items():
                try:
                    validated = await validator.validate_batch(configs, http_session, check_ping=False)

                    async with factory() as session:
                        for item in validated:
                            try:
                                if await crud.config_exists(session, item["config_hash"]):
                                    continue
                                await crud.save_config(session, source=source, **item)
                                await queue.put(item["watermarked_config"], item["country_code"])
                            except Exception as exc:
                                logger.error("Error saving config from {}: {}", source, exc)

                    # publish آخرین کانفیگ‌های DB
                    async with factory() as session:
                        rows = await crud.get_last_configs(session, SCRAPER_PUBLISH_LIMIT)
                        for row in rows:
                            config = row.watermarked_config or row.raw_config
                            await queue.put(config, row.country_code or "UN")
                except Exception as exc:
                    logger.error("Error processing source {}: {}", source, exc)

    except Exception as exc:
        logger.error("Scraper job failed: {}", exc)
    else:
        logger.info("Scraper job completed successfully")


async def post_init(application: Application) -> None:
    """راه‌اندازی DB، scheduler و publisher پس از init bot."""
    await init_db()
    await migrate_admins_json()

    Broadcaster().start()

    settings = get_settings()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        scraper_job,
        "interval",
        seconds=settings.scraper_interval,
        id="scraper",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    application.bot_data["scheduler"] = scheduler

    # اولین scrape با تأخیر کوتاه
    asyncio.create_task(scraper_job())
    logger.info("Background services started")


async def post_shutdown(application: Application) -> None:
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.shutdown(wait=False)
    broadcaster = Broadcaster()
    await broadcaster.stop()
    await close_db()
    logger.info("Shutdown complete")


def build_application() -> Application:
    settings = get_settings()
    app = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    return app


def main() -> None:
    setup_logging()
    logger.info("Starting {} ...", get_settings().project_name)
    application = build_application()
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
