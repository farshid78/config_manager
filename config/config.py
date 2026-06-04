import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """
    تنظیمات مرکزی پروژه
    """

    PROJECT_NAME = os.getenv("PROJECT_NAME")

    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # 👑 OWNER (ادمین اصلی)
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))

    DATABASE_NAME = os.getenv("DATABASE_NAME")

    LOG_LEVEL = os.getenv("LOG_LEVEL")


settings = Settings()