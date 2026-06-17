# database/models.py — مدل‌های جدول دیتابیس با SQLAlchemy 2.0
# هر کلاس یک جدول در دیتابیس را تعریف می‌کند
# از نوع‌دهی Mapped برای type-safety استفاده شده است

from datetime import datetime  # نوع تاریخ و زمان

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func  # انواع ستون و توابع SQL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # کلاس پایه و نوع‌دهی ORM


class Base(DeclarativeBase):
    """کلاس پایه برای تمام مدل‌ها — تعریف مشترک metadata.

    تمام مدل‌ها باید از این کلاس ارث‌بری کنند.
    SQLAlchemy از این metadata برای ایجاد جداول استفاده می‌کند.
    """
    pass


class User(Base):
    """جدول کاربران ربات — ذخیره اطلاعات هر کاربر.

    ستون‌ها:
    - user_id: شناسه تلگرام کاربر (کلید اصلی)
    - first_name: نام کاربر (اختیاری)
    - username: نام کاربری تلگرام (اختیاری)
    - joined_at: زمان عضویت (خودکار)
    """

    __tablename__ = "users"  # نام جدول در دیتابیس

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # شناسه تلگرام — کلید اصلی
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)  # نام — اختیاری
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)  # نام کاربری — اختیاری
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())  # زمان عضویت — خودکار


class Admin(Base):
    """جدول ادمین‌های داینامیک — مالک از .env خوانده می‌شود.

    ستون‌ها:
    - user_id: شناسه تلگرام ادمین (کلید اصلی)
    - added_at: زمان افزودن (خودکار)
    - added_by: شناسه افزودن‌کننده (اختیاری)
    """

    __tablename__ = "admins"  # نام جدول

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # شناسه ادمین — کلید اصلی
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())  # زمان افزودن — خودکار
    added_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # افزودن‌شده توسط — اختیاری


class VipUser(Base):
    """جدول کاربران VIP — دسترسی ویژه به امکانات.

    ستون‌ها:
    - user_id: شناسه تلگرام کاربر VIP (کلید اصلی)
    - added_at: زمان افزودن (خودکار)
    """

    __tablename__ = "vip_users"  # نام جدول

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # شناسه VIP — کلید اصلی
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())  # زمان افزودن — خودکار


class ProcessedConfig(Base):
    """جدول کانفیگ‌های پردازش‌شده — ذخیره کانفیگ‌های استخراج‌شده.

    ستون‌ها:
    - id: شناسه یکتا (خودافزایشی)
    - raw_config: متن اصلی کانفیگ
    - watermarked_config: کانفیگ با واترمارک (اختیاری)
    - config_hash: هش MD5 برای تشخیص تکراری
    - country_code: کد کشور سرور (اختیاری)
    - protocol: نوع پروتکل (اختیاری)
    - host: آدرس سرور (اختیاری)
    - source: منبع کانفیگ (اختیاری)
    - is_valid: آیا کانفیگ معتبر است
    - created_at: زمان ایجاد (خودکار)

    ایندکس‌ها:
    - config_hash: برای جستجوی سریع تکراری‌ها
    - country_code, protocol: برای فیلتر ترکیبی
    - created_at: برای مرتب‌سازی زمانی
    """

    __tablename__ = "processed_configs"  # نام جدول

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # شناسه — خودافزایشی
    raw_config: Mapped[str] = mapped_column(Text, nullable=False)  # متن اصلی کانفیگ — اجباری
    watermarked_config: Mapped[str | None] = mapped_column(Text, nullable=True)  # کانفیگ واترمارک‌شده — اختیاری
    config_hash: Mapped[str] = mapped_column(String(32), index=True)  # هش MD5 — ایندکس برای dedup
    country_code: Mapped[str | None] = mapped_column(String(8), index=True)  # کد کشور — ایندکس برای فیلتر
    protocol: Mapped[str | None] = mapped_column(String(32), index=True)  # نوع پروتکل — ایندکس برای فیلتر
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)  # آدرس سرور — اختیاری
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)  # منبع کانفیگ — اختیاری
    is_valid: Mapped[bool] = mapped_column(default=True)  # وضعیت اعتبار — پیش‌فرض: معتبر
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)  # زمان ایجاد — ایندکس

    __table_args__ = (  # تنظیمات اضافی جدول
        Index("ix_configs_country_protocol", "country_code", "protocol"),  # ایندکس ترکیبی کشور + پروتکل
    )


class CleanIP(Base):
    """جدول آی‌پی‌های تمیز — IP‌های جایگزین برای دور زدن فیلترینگ.

    ستون‌ها:
    - id: شناسه یکتا (خودافزایشی)
    - ip: آدرس IP تمیز (یکتا و ایندکس‌شده)
    - created_at: زمان افزودن (خودکار)
    """

    __tablename__ = "clean_ips"  # نام جدول

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # شناسه — خودافزایشی
    ip: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # آدرس IP — یکتا و ایندکس‌شده
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())  # زمان افزودن — خودکار


class UserStat(Base):
    """جدول آمار کاربران — شمارش استارت و آخرین فعالیت.

    ستون‌ها:
    - user_id: شناسه تلگرام کاربر (کلید اصلی)
    - start_count: تعداد دفعات استارت
    - last_activity: زمان آخرین فعالیت (اختیاری)
    """

    __tablename__ = "user_stats"  # نام جدول

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # شناسه کاربر — کلید اصلی
    start_count: Mapped[int] = mapped_column(Integer, default=0)  # تعداد استارت — پیش‌فرض: 0
    last_activity: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # آخرین فعالیت — اختیاری


class ScraperSource(Base):
    """جدول منابع اسکرپر — ذخیره کانال‌ها و لینک‌های اشتراک.

    ستون‌ها:
    - id: شناسه یکتا (خودافزایشی)
    - name: نام منبع (نمایشی)
    - url: آدرس منبع (نام کانال یا لینک اشتراک)
    - source_type: نوع منبع — telegram یا subscription
    - is_active: آیا منبع فعال است
    - last_scraped: زمان آخرین اسکرپ موفق (اختیاری)
    - last_config_count: تعداد کانفیگ‌های آخرین اسکرپ
    - created_at: زمان ایجاد (خودکار)
    """

    __tablename__ = "scraper_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # telegram / subscription
    is_active: Mapped[bool] = mapped_column(default=True)
    last_scraped: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_config_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
