# database/session.py — مدیریت اتصال ناهمزمان SQLAlchemy به پایگاه داده
# این ماژول موتور دیتابیس، کارخانه نشست و عملیات اولیه‌سازی را مدیریت می‌کند

from collections.abc import AsyncGenerator  # نوع Generator ناهمزمان
from contextlib import asynccontextmanager  # ساخت context manager ناهمزمان

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # SQLAlchemy ناهمزمان

from core.config import get_settings  # دریافت تنظیمات (DATABASE_URL)
from core.logger import get_logger  # سیستم لاگ‌گیری
from database.models import Base  # کلاس پایه مدل‌ها برای ایجاد جداول

logger = get_logger()  # نمونه لاگر برای این ماژول

# متغیرهای سراسری (singleton pattern) — فقط یک بار ساخته می‌شوند
_engine = None  # موتور اتصال SQLAlchemy
_session_factory: async_sessionmaker[AsyncSession] | None = None  # کارخانه نشست


def get_engine():
    """دریافت یا ساخت موتور اتصال ناهمزمان SQLAlchemy (singleton).

    موتور فقط در اولین فراخوانی ساخته می‌شود.
    تنظیمات از فایل .env خوانده می‌شوند.

    Returns:
        موتور اتصال ناهمزمان
    """
    global _engine  # دسترسی به متغیر سراسری
    if _engine is None:  # اگر موتور هنوز ساخته نشده
        settings = get_settings()  # دریافت تنظیمات
        _engine = create_async_engine(  # ساخت موتور ناهمزمان
            settings.database_url,  # نشانی اتصال به دیتابیس
            echo=False,  # لاگ SQL خاموش — لاگ‌های تمیزتر
            pool_pre_ping=True,  # بررسی اتصال قبل از هر استفاده
        )
    return _engine  # بازگرداندن موتور


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """دریافت یا ساخت کارخانه نشست SQLAlchemy (singleton).

    کارخانه نشست برای ایجاد نشست‌های جدید استفاده می‌شود.
    expire_on_commit=False: اشیاء بعد از commit قابل دسترسی باقی می‌مانند.

    Returns:
        کارخانه نشست ناهمزمان
    """
    global _session_factory  # دسترسی به متغیر سراسری
    if _session_factory is None:  # اگر کارخانه هنوز ساخته نشده
        _session_factory = async_sessionmaker(  # ساخت کارخانه نشست
            get_engine(),  # استفاده از موتور اتصال
            class_=AsyncSession,  # کلاس نشست ناهمزمان
            expire_on_commit=False,  # اشیاء بعد از commit منقضی نشوند
        )
    return _session_factory  # بازگرداندن کارخانه


@asynccontextmanager  # دکوراتور context manager ناهمزمان
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager برای نشست دیتابیس — پاکسازی خودکار.

    نشست به صورت خودکار بعد از خروج از بلوک بسته می‌شود.
    مثال:
        async with get_session_context() as session:
            result = await session.execute(query)

    Yields:
        نشست ناهمزمان SQLAlchemy
    """
    factory = get_session_factory()  # دریافت کارخانه نشست
    async with factory() as session:  # ایجاد نشست
        yield session  # تحویل نشست به بلوک caller


async def init_db() -> None:
    """ایجاد جداول دیتابیس در اولین اجرا.

    تمام جداول تعریف‌شده در database/models.py ایجاد می‌شوند.
    اگر جدول از قبل وجود داشته باشد، نادیده گرفته می‌شود.
    """
    engine = get_engine()  # دریافت موتور اتصال
    async with engine.begin() as conn:  # شروع تراکنش DDL
        await conn.run_sync(Base.metadata.create_all)  # ایجاد تمام جداول
    logger.info("Database initialized")  # لاگ موفقیت


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency برای نشست دیتابیس — استفاده در handlerها.

    این تابع به عنوان generator ناهمزمان استفاده می‌شود.
    نشست به صورت خودکار بسته می‌شود.

    Yields:
        نشست ناهمزمان SQLAlchemy
    """
    factory = get_session_factory()  # دریافت کارخانه نشست
    async with factory() as session:  # ایجاد نشست
        yield session  # تحویل نشست


async def close_db() -> None:
    """بستن اتصال دیتابیس و پاکسازی منابع.

    موتور اتصال و کارخانه نشست حذف می‌شوند.
    باید هنگام خاموش شدن برنامه فراخوانی شود.
    """
    global _engine, _session_factory  # دسترسی به متغیرهای سراسری
    if _engine is not None:  # اگر موتور فعال بود
        await _engine.dispose()  # بستن تمام اتصال‌ها
        _engine = None  # پاکسازی مرجع موتور
        _session_factory = None  # پاکسازی مرجع کارخانه
        logger.info("Database connection closed")  # لاگ بستن اتصال
