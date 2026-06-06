# core/exceptions.py — خطاهای سفارشی مرکزی


class ConfigBotError(Exception):
    """کلاس پایه تمام خطاهای پروژه."""


class ConfigurationError(ConfigBotError):
    """تنظیمات .env یا config نامعتبر است."""


class DatabaseError(ConfigBotError):
    """خطاهای لایه دیتابیس."""


class ScraperError(ConfigBotError):
    """خطاهای جمع‌آوری کانفیگ."""


class ValidationError(ConfigBotError):
    """کانفیگ نامعتبر یا ping ناموفق."""


class PublishError(ConfigBotError):
    """خطاهای انتشار در کانال."""


class AuthError(ConfigBotError):
    """دسترسی غیرمجاز."""
