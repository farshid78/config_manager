# core/logger.py — سیستم لاگ‌گیری حرفه‌ای با Loguru
# لاگ‌ها همزمان در کنسول و فایل‌های روزانه ذخیره می‌شوند

import sys  # دسترسی به stderr برای خروجی کنسول
from pathlib import Path  # کار با مسیرهای فایل

from loguru import logger  # کتابخانه لاگ‌گیری Loguru

from core.config import BASE_DIR, get_settings  # تنظیمات و مسیر پایه

# مسیر پوشه لاگ‌ها
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)  # ایجاد پوشه اگر وجود نداشت


def _is_noisy(record) -> bool:
    """فیلتر لاگ‌های پرسر و صدا — SQLAlchemy و aiohttp."""
    noisy_names = {"sqlalchemy", "aiosqlite", "aiohttp.access"}
    name = record.get("name", "")
    return not any(name.startswith(n) for n in noisy_names)


def setup_logging() -> None:
    """پیکربندی اولیه سیستم لاگ‌گیری.

    دو خروجی تنظیم می‌شود:
    1. کنسول (stderr) — فقط لاگ‌های برنامه (بدون SQL)
    2. فایل روزانه — همه لاگ‌ها شامل SQL
    """
    settings = get_settings()

    logger.remove()

    # خروجی کنسول — فقط لاگ‌های برنامه (انگلیسی برای سازگاری با کنسول ویندوز)
    logger.add(
        sys.stderr,
        level=settings.log_level,
        filter=_is_noisy,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <5}</level> | "
            "<level>{message}</level>"
        ),
    )

    # فایل روزانه — همه لاگ‌ها شامل SQLAlchemy
    logger.add(
        LOG_DIR / "bot_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",
        retention="14 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    )

    logger.info("Logging initialized | level={}", settings.log_level)


def get_logger():
    """دریافت نمونه لاگر سراسری.

    از این تابع در تمام ماژول‌ها برای دسترسی به لاگر استفاده شود.
    مثال: logger = get_logger()
    """
    return logger
