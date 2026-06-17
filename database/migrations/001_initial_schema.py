# database/migrations/001_initial_schema.py — مهاجرت اولیه به PostgreSQL
# این فایل برای ایجاد جداول اولیه در PostgreSQL استفاده می‌شود

import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.logger import get_logger

logger = get_logger()


async def upgrade(engine: AsyncEngine) -> None:
    """اجرای مهاجرت: ایجاد جداول اولیه در PostgreSQL."""

    # مسیر فایل‌های SQL
    migrations_dir = Path(__file__).parent
    schema_file = migrations_dir / "schema.sql"

    if not schema_file.exists():
        logger.error("Schema file not found: {}", schema_file)
        raise FileNotFoundError(f"Schema file not found: {schema_file}")

    # خواندن محتوای فایل SQL
    with open(schema_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    # اجرای دستورات SQL
    async with engine.begin() as conn:
        # تقسیم فایل به دستورات جداگانه (برای خطا بهتر)
        statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

        for statement in statements:
            try:
                await conn.execute(text(statement))
                logger.debug("Executed SQL statement: {}", statement[:50] + "...")
            except Exception as exc:
                logger.error("Failed to execute SQL statement: {}", statement[:50] + "...")
                raise exc

    logger.info("Database schema upgraded successfully")


async def downgrade(engine: AsyncEngine) -> None:
    """بازگرداندن مهاجرت: حذف جداول (در صورت نیاز)."""
    # در اینجا می‌توانید دستورات حذف جداول را اضافه کنید
    # برای مهاجرت اولیه، معمولاً نیازی به این تابع نیست
    logger.warning("Downgrade not implemented for initial migration")
