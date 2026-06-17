# core/ip_manager.py — مدیریت IP تمیز و اعمال آن بر کانفیگ‌ها
# این ماژول IP‌های تمیز را خوانده و جایگزین آدرس سرور در کانفیگ‌ها می‌کند

from __future__ import annotations  # پشتیبانی از type hints پیشرفته

import base64  # رمزگشایی/رمزگذاری Base64 (برای vmess)
import json  # پارس و ساخت JSON (برای vmess)
import re  # عبارات منظم (regex)
from typing import Optional  # نوع Optional

from core.logger import get_logger  # سیستم لاگ‌گیری
from core.utils import is_valid_ip  # اعتبارسنجی IPv4

logger = get_logger()  # نمونه لاگر برای این ماژول


def parse_ips_from_text(text: str) -> list[str]:
    """تجزیه و استخراج IP‌ها از متن ورودی.

    متن می‌تواند شامل IP‌ها با جداکننده خط جدید، کاما یا فاصله باشد.

    Args:
        text: متن حاوی IP‌ها
    Returns:
        لیست IP‌های معتبر
    """
    ips = []  # لیست IP‌های معتبر
    candidates = re.split(r"[\n\r,\s]+", text.strip())  # تفکیک متن بر اساس جداکننده‌ها

    for candidate in candidates:  # پیمایش هر کاندیدا
        candidate = candidate.strip()  # حذف فاصله‌های اضافی
        if candidate and is_valid_ip(candidate):  # اگر IP معتبر بود
            ips.append(candidate)  # اضافه به لیست
        elif candidate:  # اگر غیرخالی ولی نامعتبر بود
            logger.warning("Invalid IP format: {}", candidate)  # لاگ هشدار

    return ips  # بازگرداندن لیست IP‌های معتبر


async def parse_ips_from_file(file_path: str) -> list[str]:
    """خواندن و استخراج IP‌ها از فایل متنی.

    خطوط خالی و خطوطی که با # شروع شوند نادیده گرفته می‌شوند.

    Args:
        file_path: مسیر فایل حاوی IP‌ها
    Returns:
        لیست IP‌های معتبر
    Raises:
        Exception: در صورت خطا در خواندن فایل
    """
    ips = []  # لیست IP‌های معتبر
    try:
        with open(file_path, "r", encoding="utf-8") as f:  # باز کردن فایل
            for line in f:  # پیمایش هر خط
                line = line.strip()  # حذف فاصله‌های اضافی
                if not line or line.startswith("#"):  # نادیده گرفتن خطوط خالی و کامنت
                    continue
                for candidate in re.split(r"[\s,]+", line):  # تفکیک IP‌ها در هر خط
                    candidate = candidate.strip()  # حذف فاصله
                    if candidate and is_valid_ip(candidate):  # اگر IP معتبر بود
                        ips.append(candidate)  # اضافه به لیست
                    elif candidate:  # اگر نامعتبر بود
                        logger.warning("Invalid IP in file: {}", candidate)  # لاگ هشدار
    except Exception as exc:  # در صورت خطا در خواندن فایل
        logger.error("Error reading IP file {}: {}", file_path, exc)  # لاگ خطا
        raise  # بازگرداندن خطا به فراخواننده

    return ips  # بازگرداندن لیست IP‌ها


def apply_ip_to_config(config: str, ip: str) -> Optional[str]:
    """اعمال IP تمیز به کانفیگ V2Ray (جایگزینی آدرس سرور).

    - vmess: رمزگشایی Base64 → تغییر فیلد add → رمزگذاری مجدد
    - vless/trojan/ss: جایگزینی host در URL و همچنین host داخل fragment (در صورتی که الگوی پروژه باشد)

    Args:
        config: رشته کانفیگ V2Ray
        ip: آدرس IP تمیز برای جایگزینی
    Returns:
        کانفیگ اصلاح‌شده یا None در صورت عدم تغییر/خطا
    """
    try:
        config = config.strip()  # حذف فاصله‌های اضافی

        if config.startswith("vmess://"):  # اگر پروتکل vmess بود
            return _apply_ip_vmess(config, ip)  # پردازش جداگانه vmess

        # پروتکل‌های vless, trojan, ss — جایگزینی @oldhost: با @newip:
        base = config.split("#")[0].strip()  # بخش اصلی URL (بدون fragment)
        fragment = config.split("#", 1)[1] if "#" in config else ""  # بخش fragment (نام/آیتم)

        result_base = re.sub(r"@[^:]+:", f"@{ip}:", base)  # جایگزینی host با IP جدید

        if fragment:
            # در خروجی پروژه fragment معمولاً از این الگو پیروی می‌کند:
            # #{country_code}-{host}
            # پس علاوه بر URL، داخل fragment هم host را آپدیت می‌کنیم.
            oldhost = None
            m = re.search(r"@([^:]+):", base)
            if m:
                oldhost = m.group(1)

            result_fragment = fragment
            if oldhost:
                result_fragment = result_fragment.replace(f"-{oldhost}", f"-{ip}")

            result = f"{result_base}#{result_fragment}"
            return result if result != config else None

        return result_base if result_base != base else None

    except Exception as exc:  # در صورت خطا
        logger.error("Error applying IP {} to config: {}", ip, exc)  # لاگ خطا
        return None  # بازگرداندن None


def _apply_ip_vmess(config: str, ip: str) -> Optional[str]:
    """اعمال IP به کانفیگ vmess با رمزگشایی و رمزگذاری Base64.

    مراحل:
    1. حذف پیشوند vmess://
    2. رمزگشایی Base64
    3. پارس JSON
    4. تغییر فیلد add به IP جدید
    5. رمزگذاری مجدد Base64

    Args:
        config: رشته کانفیگ vmess
        ip: آدرس IP تمیز
    Returns:
        کانفیگ vmess اصلاح‌شده یا None در صورت خطا
    """
    try:
        raw = config[len("vmess://"):].strip()  # حذف پیشوند vmess://
        padding = len(raw) % 4  # محاسبه padding مورد نیاز Base64
        if padding:  # اگر padding لازم بود
            raw += "=" * (4 - padding)  # اضافه کردن کاراکترهای =

        data = json.loads(base64.b64decode(raw).decode("utf-8"))  # رمزگشایی و پارس JSON
        data["add"] = ip  # جایگزینی آدرس سرور با IP جدید

        # رمزگذاری مجدد JSON به Base64
        encoded = base64.b64encode(
            json.dumps(data, ensure_ascii=False).encode()  # تبدیل JSON به بایت
        ).decode()  # تبدیل بایت به رشته

        return f"vmess://{encoded}"  # بازگرداندن کانفیگ vmess اصلاح‌شده
    except Exception as exc:  # در صورت خطا
        logger.error("Error applying IP to vmess config: {}", exc)  # لاگ خطا
        return None  # بازگرداندن None


async def apply_ips_to_configs(
    ips: list[str],
    configs: list,
    apply_per_ip: int = 5,
) -> list[str]:
    """اعمال لیست IP‌های تمیز به کانفیگ‌ها با روتیشن.

    برای هر IP، به تعداد apply_per_ip کانفیگ انتخاب شده و IP روی آنها اعمال می‌شود.
    کانفیگ‌ها به صورت چرخشی (round-robin) انتخاب می‌شوند.

    Args:
        ips: لیست IP‌های تمیز
        configs: لیست ردیف‌های کانفیگ از دیتابیس
        apply_per_ip: تعداد کانفیگ برای هر IP (پیش‌فرض: 5)
    Returns:
        لیست کانفیگ‌های اصلاح‌شده
    """
    output_configs = []  # لیست کانفیگ‌های خروجی

    if not configs:  # اگر لیست کانفیگ‌ها خالی بود
        logger.warning("No configs to apply IPs to")  # لاگ هشدار
        return []  # بازگرداندن لیست خالی

    if not ips:  # اگر لیست IP‌ها خالی بود
        logger.warning("No IPs to apply")  # لاگ هشدار
        return []  # بازگرداندن لیست خالی

    for ip in ips:  # پیمایش هر IP
        for i in range(apply_per_ip):  # اعمال به تعداد مشخص کانفیگ
            config_row = configs[i % len(configs)]  # انتخاب چرخشی کانفیگ
            config_text = config_row.watermarked_config or config_row.raw_config  # متن کانفیگ

            modified = apply_ip_to_config(config_text, ip)  # اعمال IP به کانفیگ
            if modified:  # اگر تغییر موفق بود
                output_configs.append(modified)  # اضافه کردن کانفیگ اصلاح‌شده
            else:  # اگر تغییری نکرد
                output_configs.append(config_text)  # اضافه کردن کانفیگ اصلی

    logger.info(  # لاگ اطلاعات عملیات
        "Applied {} IPs to {} configs, output: {} configs",
        len(ips), len(configs), len(output_configs),
    )

    return output_configs  # بازگرداندن لیست کانفیگ‌های خروجی


def format_configs_as_text(configs: list[str]) -> str:
    """فرمت‌کردن لیست کانفیگ‌ها به متن واحد برای ارسال.

    کانفیگ‌ها با دو خط فاصله از هم جدا می‌شوند.

    Args:
        configs: لیست رشته‌های کانفیگ
    Returns:
        متن فرمت‌شده
    """
    return "\n\n".join(configs)  # اتصال کانفیگ‌ها با دو خط فاصله


async def cleanup_temp_files(export_dir, max_age_minutes: int = 10) -> int:
    """حذف فایل‌های موقت قدیمی‌تر از حداکثر سن مشخص‌شده.

    فایل‌هایی که با temp_ شروع شوند و قدیمی‌تر از max_age_minutes باشند حذف می‌شوند.
    این تابع برای جلوگیری از انباشت فایل‌های موقت استفاده می‌شود.

    Args:
        export_dir: مسیر پوشه فایل‌های خروجی
        max_age_minutes: حداکثر سن فایل به دقیقه (پیش‌فرض: 10)
    Returns:
        تعداد فایل‌های حذف‌شده
    """
    from pathlib import Path  # کار با مسیرهای فایل
    from datetime import datetime, timedelta, timezone  # عملیات زمانی

    deleted_count = 0  # شمارنده فایل‌های حذف‌شده
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)  # زمان مرز

    try:
        export_path = Path(export_dir)  # تبدیل به Path
        for temp_file in export_path.glob("temp_*.txt"):  # جستجوی فایل‌های موقت
            file_mtime = datetime.fromtimestamp(  # زمان آخرین تغییر فایل
                temp_file.stat().st_mtime, tz=timezone.utc
            )
            if file_mtime < cutoff_time:  # اگر فایل قدیمی‌تر از حد مجاز بود
                try:
                    temp_file.unlink()  # حذف فایل
                    deleted_count += 1  # افزایش شمارنده
                    logger.debug("Deleted temp file: {}", temp_file.name)  # لاگ دیباگ
                except Exception as exc:  # خطا در حذف فایل
                    logger.error("Error deleting temp file {}: {}", temp_file.name, exc)
    except Exception as exc:  # خطای کلی
        logger.error("Error during temp file cleanup: {}", exc)

    if deleted_count > 0:  # اگر فایلی حذف شد
        logger.info("Cleaned up {} temp files", deleted_count)  # لاگ اطلاعات

    return deleted_count  # بازگرداندن تعداد فایل‌های حذف‌شده
