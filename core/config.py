# core/config.py — تنظیمات مرکزی با pydantic-settings

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ریشه پروژه (یک سطح بالاتر از core/)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """تمام متغیرهای محیطی از .env خوانده می‌شوند."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # --- Telegram ---
    bot_token: str = Field(..., alias="BOT_TOKEN")
    owner_id: int = Field(..., alias="OWNER_ID")
    channel_username: str = Field(default="@jojo_config", alias="CHANNEL_USERNAME")

    # --- Database ---
    # SQLite پیش‌فرض برای توسعه محلی؛ در Docker از PostgreSQL استفاده کنید
    database_url: str = Field(
        default=f"sqlite+aiosqlite:///{(DATA_DIR / 'main.db').as_posix()}",
        alias="DATABASE_URL",
    )

    # --- App ---
    project_name: str = Field(default="Config Manager", alias="PROJECT_NAME")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # --- Scraper ---
    scraper_enabled: bool = Field(default=True, alias="SCRAPER_ENABLED")
    scraper_interval: int = Field(default=300, alias="SCRAPER_INTERVAL")

    @field_validator("bot_token")
    @classmethod
    def validate_token(cls, value: str) -> str:
        token = value.strip()
        placeholders = {"", "your_bot_token_here", "000000000:TEST_TOKEN_FOR_PYTEST"}
        if token in placeholders:
            raise ValueError(
                "BOT_TOKEN تنظیم نشده. در @BotFather توکن بگیرید و در .env قرار دهید."
            )
        if ":" not in token:
            raise ValueError("فرمت BOT_TOKEN نامعتبر است.")
        return token

    @field_validator("owner_id")
    @classmethod
    def validate_owner(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("OWNER_ID باید آیدی عددی تلگرام مالک باشد.")
        return value


@lru_cache
def get_settings() -> Settings:
    """Singleton تنظیمات — یک بار parse می‌شود."""
    return Settings()
