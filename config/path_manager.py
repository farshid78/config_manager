# config/path_manager.py

from pathlib import Path


# ریشه پروژه
BASE_DIR = Path(__file__).resolve().parent.parent


class Paths:

    # پوشه‌ها
    APP = BASE_DIR / "app"

    CONFIG = BASE_DIR / "config"

    DATABASE = BASE_DIR / "database"

    STORAGE = BASE_DIR / "storage"

    CACHE = BASE_DIR / "cache"

    LOGS = BASE_DIR / "logs"

    EXPORTS = BASE_DIR / "exports"

    TESTS = BASE_DIR / "tests"

    SHARED_MEMORY = BASE_DIR / "shared_memory"

    # فایل‌ها
    DATABASE_FILE = DATABASE / "main.db"

    USERS_JSON = STORAGE / "users.json"

    CONFIGS_JSON = STORAGE / "configs.json"

    STATS_JSON = STORAGE / "stats.json"


paths = Paths()