# core/config.py — تنظیمات مرکزی برنامه با pydantic-settings
# تمام متغیرهای محیطی از فایل .env خوانده می‌شوند و اعتبارسنجی می‌گردند

from functools import lru_cache  # کش‌کردن نتیجه تابع (singleton pattern)
from pathlib import Path  # کار با مسیرهای فایل

from pydantic import Field, field_validator  # اعتبارسنجی و تعریف فیلدها
from pydantic_settings import BaseSettings, SettingsConfigDict  # پایه تنظیمات با pydantic

# ریشه پروژه (یک سطح بالاتر از پوشه core/)
BASE_DIR = Path(__file__).resolve().parent.parent
# مسیر پوشه داده‌ها (دیتابیس، لاگ، خروجی‌ها)
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)  # ایجاد پوشه data اگر وجود نداشت


class Settings(BaseSettings):
    """کلاس تنظیمات برنامه — تمام متغیرها از فایل .env خوانده می‌شوند.

    هر فیلد یک alias دارد که نام متغیر محیطی متناظر است.
    مقادیر پیش‌فرض برای فیلدهای اختیاری تعریف شده‌اند.
    """

    model_config = SettingsConfigDict(  # پیکربندی خواندن تنظیمات
        env_file=BASE_DIR / ".env",  # مسیر فایل .env
        env_file_encoding="utf-8",  # رمزگذاری فایل .env
        extra="ignore",  # نادیده گرفتن متغیرهای اضافی در .env
        populate_by_name=True,  # اجازه پرکردن با نام فیلد یا alias
    )

    # --- تنظیمات تلگرام ---
    bot_token: str = Field(..., alias="BOT_TOKEN")  # توکن ربات (اجباری — از @BotFather)
    owner_id: int = Field(..., alias="OWNER_ID")  # آیدی عددی مالک ربات (اجباری)
    channel_username: str = Field(default="@jojo_config", alias="CHANNEL_USERNAME")  # نام کانال انتشار

    # --- تنظیمات پایگاه داده ---
    # SQLite پیش‌فرض برای توسعه محلی؛ در Docker از PostgreSQL استفاده کنید
    database_url: str = Field(  # نشانی اتصال به دیتابیس
        default=f"sqlite+aiosqlite:///{(DATA_DIR / 'main.db').as_posix()}",  # پیش‌فرض: SQLite محلی
        alias="DATABASE_URL",  # نام متغیر محیطی
    )

    # --- تنظیمات عمومی برنامه ---
    project_name: str = Field(default="Config Manager", alias="PROJECT_NAME")  # نام پروژه
    debug: bool = Field(default=False, alias="DEBUG")  # حالت دیباگ (لاگ‌های بیشتر)
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")  # سطح لاگ‌گیری

    # --- تنظیمات اسکرپر ---
    scraper_enabled: bool = Field(default=True, alias="SCRAPER_ENABLED")  # فعال/غیرفعال بودن اسکرپر
    scraper_interval: int = Field(default=300, alias="SCRAPER_INTERVAL")  # فاصله زمانی اسکرپر (ثانیه)
    scraper_proxy: str = Field(default="", alias="SCRAPER_PROXY")  # آدرس پروکسی HTTP (مثل http://127.0.0.1:10808)

    @field_validator("bot_token")  # اعتبارسنج توکن ربات
    @classmethod
    def validate_token(cls, value: str) -> str:
        """بررسی صحت توکن ربات تلگرام.

        - توکن نباید خالی یا placeholder باشد
        - باید شامل کاراکتر ':' باشد (فرمت استاندارد تلگرام)
        """
        token = value.strip()  # حذف فاصله‌های اضافی
        placeholders = {"", "your_bot_token_here", "000000000:TEST_TOKEN_FOR_PYTEST"}  # مقادیر نامعتبر
        if token in placeholders:  # اگر توکن placeholder بود
            raise ValueError(
                "BOT_TOKEN تنظیم نشده. در @BotFather توکن بگیرید و در .env قرار دهید."
            )
        if ":" not in token:  # فرمت توکن باید شامل : باشد
            raise ValueError("فرمت BOT_TOKEN نامعتبر است.")
        return token  # بازگرداندن توکن معتبر

    @field_validator("owner_id")  # اعتبارسنج آیدی مالک
    @classmethod
    def validate_owner(cls, value: int) -> int:
        """بررسی صحت آیدی مالک ربات.

        - آیدی باید عدد مثبت باشد (آیدی تلگرام همیشه مثبت است)
        """
        if value <= 0:  # آیدی نامعتبر
            raise ValueError("OWNER_ID باید آیدی عددی تلگرام مالک باشد.")
        return value  # بازگرداندن آیدی معتبر


@lru_cache  # کش‌کردن نتیجه — تنظیمات فقط یک بار ساخته می‌شوند (singleton)
def get_settings() -> Settings:
    """دریافت نمونه singleton تنظیمات.

    اولین فراخوانی: ساخت نمونه Settings و خواندن .env
    فراخوانی‌های بعدی: بازگرداندن همان نمونه کش‌شده
    """
    return Settings()
