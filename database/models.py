# database/models.py — مدل‌های SQLAlchemy 2.0

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """کاربران ربات."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Admin(Base):
    """ادمین‌های داینامیک (owner از .env)."""

    __tablename__ = "admins"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


class VipUser(Base):
    """کاربران VIP."""

    __tablename__ = "vip_users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProcessedConfig(Base):
    """کانفیگ‌های پردازش‌شده."""

    __tablename__ = "processed_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_config: Mapped[str] = mapped_column(Text, nullable=False)
    watermarked_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_hash: Mapped[str] = mapped_column(String(32), index=True)
    country_code: Mapped[str | None] = mapped_column(String(8), index=True)
    protocol: Mapped[str | None] = mapped_column(String(32), index=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_valid: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_configs_country_protocol", "country_code", "protocol"),
    )


class CleanIP(Base):
    """آی‌پی‌های تمیز."""

    __tablename__ = "clean_ips"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ip: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserStat(Base):
    """آمار استارت کاربران."""

    __tablename__ = "user_stats"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    start_count: Mapped[int] = mapped_column(Integer, default=0)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
