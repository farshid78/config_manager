# core/exceptions.py — خطاهای سفارشی پروژه
# تمام خطاهای اختصاصی از کلاس پایه ConfigBotError ارث‌بری می‌کنند
# این ساختار امکان catch کردن اختصاصی هر نوع خطا را فراهم می‌کند


class ConfigBotError(Exception):
    """کلاس پایه تمام خطاهای سفارشی پروژه.

    تمام خطاهای اختصاصی باید از این کلاس ارث‌بری کنند.
    مثال استفاده: except ConfigBotError as e:
    """


class ConfigurationError(ConfigBotError):
    """خطای تنظیمات — فایل .env یا مقادیر پیکربندی نامعتبر است.

    مثال: BOT_TOKEN خالی یا OWNER_ID نامعتبر
    """


class DatabaseError(ConfigBotError):
    """خطای پایگاه داده — خطاهای مربوط به عملیات دیتابیس.

    مثال: خطای اتصال، خطای کوئری، خطای نشست
    """


class ScraperError(ConfigBotError):
    """خطای اسکرپر — خطاهای مربوط به جمع‌آوری کانفیگ.

    مثال: خطای HTTP، خطای پارس HTML، قطعی ارتباط
    """


class ValidationError(ConfigBotError):
    """خطای اعتبارسنجی — کانفیگ نامعتبر یا تست اتصال ناموفق.

    مثال: فرمت کانفیگ اشتباه، عدم پاسخ‌دهی سرور
    """


class PublishError(ConfigBotError):
    """خطای انتشار — خطاهای مربوط به ارسال کانفیگ در کانال.

    مثال: خطای FloodLimit تلگرام، خطای ارسال پیام
    """


class AuthError(ConfigBotError):
    """خطای احراز هویت — دسترسی غیرمجاز به منابع محدود.

    مثال: کاربر غیرادمین سعی در دسترسی به پنل ادمین
    """
