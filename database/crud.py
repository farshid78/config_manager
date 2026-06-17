# database/crud.py — عملیات CRUD (ایجاد، خواندن، به‌روزرسانی، حذف) دیتابیس
# تمام تعاملات با دیتابیس از طریق این توابع انجام می‌شود
# هر تابع یک نشست AsyncSession دریافت کرده و عملیات ناهمزمان انجام می‌دهد

from datetime import datetime, timedelta, timezone  # انواع تاریخ و زمان

from sqlalchemy import desc, func, select  # توابع کوئری SQLAlchemy
from sqlalchemy.ext.asyncio import AsyncSession  # نشست ناهمزمان

from database.models import Admin, CleanIP, ProcessedConfig, ScraperSource, User, UserStat, VipUser  # مدل‌های جدول


def _utcnow() -> datetime:
    """دریافت زمان فعلی UTC — تابع کمکی داخلی."""
    return datetime.now(timezone.utc)  # زمان فعلی با منطقه زمانی UTC


# ─── عملیات کاربران ────────────────────────────────────────


async def upsert_user(
    session: AsyncSession,
    user_id: int,
    first_name: str | None,
    username: str | None,
) -> None:
    """درج یا به‌روزرسانی کاربر (upsert).

    اگر کاربر قبلاً وجود نداشته باشد، ایجاد می‌شود.
    در غیر این صورت نام و نام کاربری به‌روزرسانی می‌شود.

    Args:
        session: نشست دیتابیس
        user_id: شناسه تلگرام کاربر
        first_name: نام کاربر
        username: نام کاربری تلگرام
    """
    existing = await session.get(User, user_id)  # جستجوی کاربر موجود
    if existing is None:  # اگر کاربر جدید بود
        session.add(User(user_id=user_id, first_name=first_name, username=username))  # ایجاد کاربر
    else:  # اگر کاربر قبلاً وجود داشت
        existing.first_name = first_name  # به‌روزرسانی نام
        existing.username = username  # به‌روزرسانی نام کاربری
    await session.commit()  # ذخیره تغییرات


async def get_all_user_ids(session: AsyncSession) -> list[int]:
    """دریافت لیست تمام شناسه‌های کاربران.

    Args:
        session: نشست دیتابیس
    Returns:
        لیست شناسه‌های تلگرام کاربران
    """
    result = await session.execute(select(User.user_id))  # کوئری شناسه‌ها
    return [row[0] for row in result.all()]  # استخراج و بازگرداندن لیست


async def count_users(session: AsyncSession) -> int:
    """شمارش تعداد کل کاربران.

    Args:
        session: نشست دیتابیس
    Returns:
        تعداد کل کاربران
    """
    result = await session.execute(select(func.count(User.user_id)))  # کوئری شمارش
    return result.scalar_one()  # بازگرداندن عدد


async def bump_user_start(session: AsyncSession, user_id: int) -> None:
    """افزایش شمارنده استارت کاربر و به‌روزرسانی آخرین فعالیت.

    اگر رکورد آمار کاربر وجود نداشته باشد، ایجاد می‌شود.

    Args:
        session: نشست دیتابیس
        user_id: شناسه تلگرام کاربر
    """
    stat = await session.get(UserStat, user_id)  # جستجوی رکورد آمار
    now = _utcnow()  # زمان فعلی UTC
    if stat is None:  # اگر رکورد آمار وجود نداشت
        session.add(UserStat(user_id=user_id, start_count=1, last_activity=now))  # ایجاد رکورد جدید
    else:  # اگر رکورد وجود داشت
        stat.start_count += 1  # افزایش شمارنده
        stat.last_activity = now  # به‌روزرسانی آخرین فعالیت
    await session.commit()  # ذخیره تغییرات


async def total_starts(session: AsyncSession) -> int:
    """محاسبه مجموع کل استارت‌های تمام کاربران.

    Args:
        session: نشست دیتابیس
    Returns:
        مجموع تعداد استارت‌ها
    """
    result = await session.execute(select(func.coalesce(func.sum(UserStat.start_count), 0)))  # مجموع با پیش‌فرض 0
    return int(result.scalar_one())  # تبدیل به عدد صحیح


# ─── عملیات ادمین‌ها ───────────────────────────────────────


async def get_admin_ids(session: AsyncSession) -> set[int]:
    """دریافت مجموعه شناسه‌های تمام ادمین‌ها.

    Args:
        session: نشست دیتابیس
    Returns:
        مجموعه شناسه‌های ادمین
    """
    result = await session.execute(select(Admin.user_id))  # کوئری شناسه‌ها
    return {row[0] for row in result.all()}  # تبدیل به مجموعه (set)


async def add_admin(session: AsyncSession, user_id: int, added_by: int) -> bool:
    """افزودن ادمین جدید.

    Args:
        session: نشست دیتابیس
        user_id: شناسه تلگرام ادمین جدید
        added_by: شناسه افزودن‌کننده
    Returns:
        True اگر اضافه شد، False اگر قبلاً وجود داشت
    """
    if await session.get(Admin, user_id):  # بررسی وجود قبلی
        return False  # ادمین قبلاً وجود دارد
    session.add(Admin(user_id=user_id, added_by=added_by))  # ایجاد رکورد ادمین
    await session.commit()  # ذخیره تغییرات
    return True  # اضافه‌شدن موفق


async def remove_admin(session: AsyncSession, user_id: int) -> bool:
    """حذف ادمین.

    Args:
        session: نشست دیتابیس
        user_id: شناسه تلگرام ادمین
    Returns:
        True اگر حذف شد، False اگر وجود نداشت
    """
    admin = await session.get(Admin, user_id)  # جستجوی ادمین
    if admin is None:  # اگر ادمین وجود نداشت
        return False
    await session.delete(admin)  # حذف رکورد
    await session.commit()  # ذخیره تغییرات
    return True  # حذف موفق


async def list_admins_with_info(session: AsyncSession) -> list[Admin]:
    """دریافت لیست ادمین‌ها با اطلاعات کامل، مرتب‌شده بر اساس جدیدترین.

    Args:
        session: نشست دیتابیس
    Returns:
        لیست اشیاء Admin
    """
    result = await session.execute(
        select(Admin).order_by(desc(Admin.added_at))  # مرتب‌سازی نزولی بر اساس زمان افزودن
    )
    return list(result.scalars().all())  # تبدیل به لیست


# ─── عملیات VIP ────────────────────────────────────────────


async def add_vip(session: AsyncSession, user_id: int) -> None:
    """افزودن کاربر VIP (اگر قبلاً VIP نباشد).

    Args:
        session: نشست دیتابیس
        user_id: شناسه تلگرام کاربر
    """
    if await session.get(VipUser, user_id) is None:  # بررسی عدم وجود قبلی
        session.add(VipUser(user_id=user_id))  # ایجاد رکورد VIP
        await session.commit()  # ذخیره تغییرات


async def remove_vip(session: AsyncSession, user_id: int) -> bool:
    """حذف کاربر VIP.

    Args:
        session: نشست دیتابیس
        user_id: شناسه تلگرام کاربر
    Returns:
        True اگر حذف شد، False اگر VIP نبود
    """
    vip = await session.get(VipUser, user_id)  # جستجوی VIP
    if vip is None:  # اگر VIP نبود
        return False
    await session.delete(vip)  # حذف رکورد
    await session.commit()  # ذخیره تغییرات
    return True  # حذف موفق


async def list_vips(session: AsyncSession, limit: int = 50) -> list[VipUser]:
    """دریافت لیست کاربران VIP.

    Args:
        session: نشست دیتابیس
        limit: حداکثر تعداد نتایج
    Returns:
        لیست اشیاء VipUser
    """
    result = await session.execute(
        select(VipUser).order_by(desc(VipUser.added_at)).limit(limit)  # مرتب‌سازی نزولی
    )
    return list(result.scalars().all())  # تبدیل به لیست


async def get_vip_ids(session: AsyncSession) -> list[int]:
    """دریافت لیست شناسه‌های کاربران VIP.

    Args:
        session: نشست دیتابیس
    Returns:
        لیست شناسه‌های VIP
    """
    result = await session.execute(select(VipUser.user_id))  # کوئری شناسه‌ها
    return [row[0] for row in result.all()]  # استخراج و بازگرداندن لیست


# ─── عملیات کانفیگ‌ها ──────────────────────────────────────


async def config_exists(session: AsyncSession, config_hash: str) -> bool:
    """بررسی وجود کانفیگ بر اساس هش (برای جلوگیری از تکراری).

    Args:
        session: نشست دیتابیس
        config_hash: هش MD5 کانفیگ
    Returns:
        True اگر کانفیگ قبلاً ذخیره شده
    """
    result = await session.execute(
        select(ProcessedConfig.id).where(ProcessedConfig.config_hash == config_hash).limit(1)  # جستجو با هش
    )
    return result.scalar_one_or_none() is not None  # True اگر نتیجه وجود داشت


async def save_config(
    session: AsyncSession,
    *,
    raw_config: str,
    watermarked_config: str,
    config_hash: str,
    country_code: str | None,
    protocol: str | None,
    host: str | None,
    source: str | None,
    is_valid: bool = True,
) -> ProcessedConfig:
    """ذخیره کانفیگ پردازش‌شده در دیتابیس.

    Args:
        session: نشست دیتابیس
        raw_config: متن اصلی کانفیگ
        watermarked_config: کانفیگ با واترمارک
        config_hash: هش MD5 برای تشخیص تکراری
        country_code: کد کشور سرور
        protocol: نوع پروتکل
        host: آدرس سرور
        source: منبع کانفیگ
        is_valid: آیا کانفیگ معتبر است
    Returns:
        شیء ProcessedConfig ذخیره‌شده
    """
    row = ProcessedConfig(  # ایجاد ردیف جدید
        raw_config=raw_config,  # متن اصلی
        watermarked_config=watermarked_config,  # واترمارک‌شده
        config_hash=config_hash,  # هش
        country_code=country_code,  # کشور
        protocol=protocol,  # پروتکل
        host=host,  # سرور
        source=source,  # منبع
        is_valid=is_valid,  # اعتبار
    )
    session.add(row)  # اضافه کردن به نشست
    await session.commit()  # ذخیره در دیتابیس
    await session.refresh(row)  # بروزرسانی شیء با مقادیر دیتابیس (مثل id)
    return row  # بازگرداندن ردیف ذخیره‌شده


async def get_last_configs(session: AsyncSession, limit: int) -> list[ProcessedConfig]:
    """دریافت آخرین کانفیگ‌های معتبر.

    Args:
        session: نشست دیتابیس
        limit: حداکثر تعداد نتایج
    Returns:
        لیست کانفیگ‌های اخیر
    """
    result = await session.execute(
        select(ProcessedConfig)
        .where(ProcessedConfig.is_valid)  # فقط کانفیگ‌های معتبر
        .order_by(desc(ProcessedConfig.id))  # جدیدترین اول
        .limit(limit)  # محدودیت تعداد
    )
    return list(result.scalars().all())  # تبدیل به لیست


async def filter_configs(
    session: AsyncSession,
    *,
    country_code: str | None = None,
    protocol: str | None = None,
    limit: int = 1000,
) -> list[ProcessedConfig]:
    """فیلتر کانفیگ‌ها بر اساس کشور و/یا پروتکل.

    Args:
        session: نشست دیتابیس
        country_code: کد کشور برای فیلتر (اختیاری)
        protocol: نام پروتکل برای فیلتر (اختیاری)
        limit: حداکثر تعداد نتایج
    Returns:
        لیست کانفیگ‌های فیلترشده
    """
    query = select(ProcessedConfig).where(ProcessedConfig.is_valid)  # فقط معتبرها
    if country_code:  # اگر فیلتر کشور مشخص بود
        query = query.where(ProcessedConfig.country_code == country_code.upper())  # فیلتر کشور (حروف بزرگ)
    if protocol:  # اگر فیلتر پروتکل مشخص بود
        query = query.where(ProcessedConfig.protocol == protocol.lower())  # فیلتر پروتکل (حروف کوچک)
    query = query.order_by(desc(ProcessedConfig.id)).limit(limit)  # مرتب‌سازی و محدودیت
    result = await session.execute(query)  # اجرای کوئری
    return list(result.scalars().all())  # تبدیل به لیست


async def count_configs(session: AsyncSession) -> int:
    """شمارش تعداد کل کانفیگ‌ها.

    Args:
        session: نشست دیتابیس
    Returns:
        تعداد کل کانفیگ‌ها
    """
    result = await session.execute(select(func.count(ProcessedConfig.id)))  # کوئری شمارش
    return result.scalar_one()  # بازگرداندن عدد


# ─── عملیات آی‌پی تمیز ─────────────────────────────────────


async def add_clean_ip(session: AsyncSession, ip: str) -> None:
    """افزودن آی‌پی تمیز (اگر قبلاً وجود نداشته باشد).

    Args:
        session: نشست دیتابیس
        ip: آدرس IPv4 تمیز
    """
    existing = (  # بررسی وجود قبلی
        await session.execute(select(CleanIP).where(CleanIP.ip == ip).limit(1))  # جستجو با IP
    ).scalar_one_or_none()  # نتیجه یا None
    if existing:  # اگر IP قبلاً ثبت شده
        return  # بدون تغییر خروج
    session.add(CleanIP(ip=ip))  # ایجاد رکورد جدید
    await session.commit()  # ذخیره تغییرات


async def count_clean_ips(session: AsyncSession) -> int:
    """شمارش تعداد کل آی‌پی‌های تمیز.

    Args:
        session: نشست دیتابیس
    Returns:
        تعداد آی‌پی‌های تمیز
    """
    result = await session.execute(select(func.count(CleanIP.id)))  # کوئری شمارش
    return result.scalar_one()  # بازگرداندن عدد


async def get_clean_ips(session: AsyncSession, limit: int = 5000) -> list[str]:
    """دریافت لیست آی‌پی‌های تمیز، مرتب‌شده بر اساس جدیدترین.

    Args:
        session: نشست دیتابیس
        limit: حداکثر تعداد نتایج
    Returns:
        لیست آدرس‌های IP
    """
    result = await session.execute(
        select(CleanIP.ip).order_by(desc(CleanIP.created_at)).limit(limit)  # جدیدترین اول
    )
    return [row[0] for row in result.all()]  # استخراج و بازگرداندن لیست


async def delete_old_clean_ips(session: AsyncSession, days: int = 5) -> int:
    """حذف آی‌پی‌های تمیز قدیمی‌تر از تعداد روز مشخص.

    Args:
        session: نشست دیتابیس
        days: تعداد روز برای نگهداری (پیش‌فرض: 5 روز)
    Returns:
        تعداد رکوردهای حذف‌شده
    """
    cutoff = _utcnow() - timedelta(days=days)
    result = await session.execute(select(CleanIP).where(CleanIP.created_at < cutoff))
    rows = list(result.scalars().all())
    for row in rows:
        await session.delete(row)
    await session.commit()
    return len(rows)


# ─── عملیات منابع اسکرپر ────────────────────────────────────────


async def add_scraper_source(
    session: AsyncSession,
    name: str,
    url: str,
    source_type: str,
) -> str:
    """افزودن منبع اسکرپر جدید.

    Args:
        session: نشست دیتابیس
        name: نام منبع
        url: آدرس منبع (نام کانال یا لینک اشتراک)
        source_type: نوع منبع — telegram یا subscription
    Returns:
        "added" اگر اضافه شد
        "duplicate_url" اگر URL تکراری بود
        "duplicate_name" اگر نام تکراری بود
    """
    # بررسی تکراری بودن URL
    existing_url = await session.execute(
        select(ScraperSource).where(ScraperSource.url == url)
    )
    if existing_url.scalar_one_or_none():
        return "duplicate_url"

    # بررسی تکراری بودن نام
    existing_name = await session.execute(
        select(ScraperSource).where(ScraperSource.name == name)
    )
    if existing_name.scalar_one_or_none():
        return "duplicate_name"

    source = ScraperSource(name=name, url=url, source_type=source_type)
    session.add(source)
    await session.commit()
    return "added"


async def remove_scraper_source(session: AsyncSession, source_id: int) -> bool:
    """حذف منبع اسکرپر با شناسه.

    Args:
        session: نشست دیتابیس
        source_id: شناسه منبع
    Returns:
        True اگر حذف شد، False اگر یافت نشد
    """
    result = await session.execute(
        select(ScraperSource).where(ScraperSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        return False
    await session.delete(source)
    await session.commit()
    return True


async def list_scraper_sources(session: AsyncSession) -> list[ScraperSource]:
    """دریافت لیست تمام منابع اسکرپر.

    Args:
        session: نشست دیتابیس
    Returns:
        لیست منابع اسکرپر
    """
    result = await session.execute(
        select(ScraperSource).order_by(ScraperSource.source_type, ScraperSource.name)
    )
    return list(result.scalars().all())


async def get_active_scraper_sources(session: AsyncSession) -> list[ScraperSource]:
    """دریافت منابع فعال اسکرپر.

    Args:
        session: نشست دیتابیس
    Returns:
        لیست منابع فعال
    """
    result = await session.execute(
        select(ScraperSource)
        .where(ScraperSource.is_active == True)
        .order_by(ScraperSource.source_type, ScraperSource.name)
    )
    return list(result.scalars().all())


async def toggle_scraper_source(session: AsyncSession, source_id: int) -> ScraperSource | None:
    """تغییر وضعیت فعال/غیرفعال منبع اسکرپر.

    Args:
        session: نشست دیتابیس
        source_id: شناسه منبع
    Returns:
        شیء ScraperSource به‌روزرسانی‌شده یا None اگر یافت نشد
    """
    result = await session.execute(
        select(ScraperSource).where(ScraperSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        return None
    source.is_active = not source.is_active
    await session.commit()
    await session.refresh(source)
    return source


async def batch_exists_hashes(session: AsyncSession, hashes: list[str]) -> set[str]:
    """بررسی دسته‌ای وجود هش‌ها — یک کوئری به جای N کوئری.

    Args:
        session: نشست دیتابیس
        hashes: لیست هش‌های MD5
    Returns:
        مجموعه هش‌هایی که قبلاً ذخیره شده‌اند
    """
    if not hashes:
        return set()
    result = await session.execute(
        select(ProcessedConfig.config_hash).where(ProcessedConfig.config_hash.in_(hashes))
    )
    return {row[0] for row in result.all()}


async def batch_save_configs(
    session: AsyncSession,
    configs: list[dict],
    source: str | None = None,
) -> tuple[int, list[dict]]:
    """ذخیره دسته‌ای کانفیگ‌ها — یک commit به جای N commit.

    ابتدا هش‌های تکراری فیلتر می‌شوند، سپس کانفیگ‌های جدید
    در یک تراکنش ذخیره می‌شوند.

    خروجی:
    - new_count: تعداد کانفیگ‌های جدید که واقعاً ذخیره شدند
    - new_configs: همان لیست دیکشنری‌های جدید (برای enqueue/ publish دقیقاً همان‌ها)

    Args:
        session: نشست دیتابیس
        configs: لیست دیکشنری‌های کانفیگ (از validate_batch)
        source: نام منبع
    Returns:
        (تعداد کانفیگ‌های جدید ذخیره‌شده, لیست کانفیگ‌های جدید)
    """
    if not configs:
        return 0, []

    # بررسی دسته‌ای هش‌های تکراری
    hashes = [c["config_hash"] for c in configs]
    existing = await batch_exists_hashes(session, hashes)

    # فیلتر کانفیگ‌های جدید (strict idempotency by config_hash)
    new_configs = [c for c in configs if c["config_hash"] not in existing]
    if not new_configs:
        return 0, []

    # ذخیره دسته‌ای
    for item in new_configs:
        row = ProcessedConfig(
            raw_config=item["raw_config"],
            watermarked_config=item["watermarked_config"],
            config_hash=item["config_hash"],
            country_code=item.get("country_code"),
            protocol=item.get("protocol"),
            host=item.get("host"),
            source=source,
            is_valid=True,
        )
        session.add(row)

    await session.commit()
    return len(new_configs), new_configs


async def update_scraper_source_stats(
    session: AsyncSession,
    source_url: str,
    config_count: int,
) -> None:
    """به‌روزرسانی آمار آخرین اسکرپ منبع.

    Args:
        session: نشست دیتابیس
        source_url: آدرس منبع
        config_count: تعداد کانفیگ‌های استخراج‌شده
    """
    result = await session.execute(
        select(ScraperSource).where(ScraperSource.url == source_url)
    )
    source = result.scalar_one_or_none()
    if source:
        source.last_scraped = _utcnow()
        source.last_config_count = config_count
        await session.commit()
