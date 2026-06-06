# core/logger.py — لاگ حرفه‌ای با Loguru

import sys
from pathlib import Path

from loguru import logger

from core.config import BASE_DIR, get_settings


LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    """پیکربندی Loguru: کنسول + فایل با rotation."""
    settings = get_settings()

    logger.remove()

    # خروجی کنسول
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # فایل روزانه با rotation
    logger.add(
        LOG_DIR / "bot_{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        rotation="00:00",
        retention="14 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    )

    logger.info("Logging initialized | level={}", settings.log_level)


def get_logger():
    return logger
