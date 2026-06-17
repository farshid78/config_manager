# database/migrations/manager.py — مدیریت مهاجرت‌های پایگاه داده
# این ماژول برای اجرای مهاجرت‌ها و مدیریت نسخه دیتابیس استفاده می‌شود

import asyncio
import importlib
import os
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from core.config import get_settings
from core.logger import get_logger

logger = get_logger()


class MigrationManager:
    """مدیریت مهاجرت‌های پایگاه داده."""

    def __init__(self, engine: AsyncEngine):
        """مقداردهی اولیه مدیر مهاجرت‌ها.

        Args:
            engine: موتور اتصال به پایگاه داده
        """
        self.engine = engine
        self.settings = get_settings()
        self.migrations_dir = Path(__file__).parent
        self._applied_migrations: Dict[str, str] = {}

    async def initialize(self) -> None:
        """آماده‌سازی جدول مهاجرت‌ها."""
        async with self.engine.begin() as conn:
            # ایجاد جدول برای ردیابی مهاجرت‌های اعمال شده
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # خواندن مهاجرت‌های اعمال شده
            result = await conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
            self._applied_migrations = {row[0]: row[0] for row in result.fetchall()}

        logger.info("Migration manager initialized")

    async def get_migration_files(self) -> List[Path]:
        """دریافت لیست فایل‌های مهاجرت به ترتیب."""
        migration_files = []

        # یافتن فایل‌های مهاجرت
        for file_path in self.migrations_dir.glob("*.py"):
            if file_path.name != "__init__.py":
                migration_files.append(file_path)

        # مرتب‌سازی بر اساس نام فایل (که شامل شماره نسخه است)
        migration_files.sort(key=lambda f: f.name)

        return migration_files

    async def get_pending_migrations(self) -> List[Path]:
        """دریافت لیست مهاجرت‌های اعمال نشده."""
        migration_files = await self.get_migration_files()
        pending = []

        for file_path in migration_files:
            version = file_path.stem
            if version not in self._applied_migrations:
                pending.append(file_path)

        return pending

    async def apply_migration(self, migration_file: Path) -> None:
        """اعمال یک مهاجرت مشخص."""
        version = migration_file.stem

        try:
            # بارگذاری ماژول مهاجرت
            module_name = f"database.migrations.{version}"
            module = importlib.import_module(module_name)

            # اجرای تابع upgrade
            if hasattr(module, "upgrade"):
                logger.info("Applying migration: {}", version)
                await module.upgrade(self.engine)

                # ثبت مهاجرت در پایگاه داده
                async with self.engine.begin() as conn:
                    await conn.execute(
                        text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                        {"version": version}
                    )

                self._applied_migrations[version] = version
                logger.info("Migration applied successfully: {}", version)
            else:
                logger.error("Migration module missing upgrade function: {}", version)

        except Exception as exc:
            logger.error("Failed to apply migration {}: {}", version, exc)
            raise exc

    async def rollback_migration(self, version: str) -> None:
        """بازگرداندن یک مهاجرت (در صورت وجود)."""
        try:
            # بارگذاری ماژول مهاجرت
            module_name = f"database.migrations.{version}"
            module = importlib.import_module(module_name)

            # اجرای تابع downgrade
            if hasattr(module, "downgrade"):
                logger.info("Rolling back migration: {}", version)
                await module.downgrade(self.engine)

                # حذف مهاجرت از پایگاه داده
                async with self.engine.begin() as conn:
                    await conn.execute(
                        text("DELETE FROM schema_migrations WHERE version = :version"),
                        {"version": version}
                    )

                if version in self._applied_migrations:
                    del self._applied_migrations[version]

                logger.info("Migration rolled back successfully: {}", version)
            else:
                logger.error("Migration module missing downgrade function: {}", version)

        except Exception as exc:
            logger.error("Failed to rollback migration {}: {}", version, exc)
            raise exc

    async def apply_all_pending(self) -> None:
        """اعمال تمام مهاجرت‌های معلق."""
        pending = await self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return

        logger.info("Applying {} pending migrations", len(pending))

        for migration_file in pending:
            await self.apply_migration(migration_file)

    async def get_migration_status(self) -> Dict[str, any]:
        """دریافت وضعیت مهاجرت‌ها."""
        migration_files = await self.get_migration_files()
        pending = await self.get_pending_migrations()

        return {
            "total_migrations": len(migration_files),
            "applied_migrations": len(self._applied_migrations),
            "pending_migrations": len(pending),
            "latest_version": migration_files[-1].stem if migration_files else None,
            "applied_versions": list(self._applied_migrations.keys())
        }


async def run_migrations() -> None:
    """اجرای تمام مهاجرت‌های معلق."""
    from database.connection import create_engine

    engine = create_engine()
    manager = MigrationManager(engine)

    try:
        await manager.initialize()
        await manager.apply_all_pending()
        logger.info("All migrations applied successfully")
    finally:
        await engine.dispose()
