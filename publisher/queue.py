# publisher/queue.py — صف ناهمزمان برای انتشار کانفیگ‌ها در کانال
# از الگوی Singleton برای دسترسی سراسری استفاده می‌شود
# صف دارای محدودیت حجم (backpressure) برای جلوگیری از مصرف بیش از حد حافظه است

from __future__ import annotations  # پشتیبانی از type hints پیشرفته

import asyncio  # صف ناهمزمان
from dataclasses import dataclass  # کلاس داده‌ای سبک


@dataclass  # دکوراتور dataclass برای ساخت خودکار __init__
class PublishItem:
    """یک آیتم در صف انتشار — شامل متن کانفیگ و کد کشور.

    Attributes:
        config: متن کانفیگ V2Ray (با واترمارک)
        country_code: کد کشور دو حرفی (مثل IR, US)
    """
    config: str  # متن کانفیگ
    country_code: str  # کد کشور


class PublishQueue:
    """صف انتشار کانفیگ‌ها — الگوی Singleton با backpressure.

    فقط یک نمونه از این کلاس در کل برنامه وجود دارد.
    صف محدود به maxsize آیتم است — اگر پر شود،
    تولیدکننده‌ها صبر می‌کنند تا جای خالی ایجاد شود.

    از None به عنوان سیگنال توقف استفاده می‌شود.
    """

    _instance: PublishQueue | None = None  # نمونه singleton

    def __init__(self, maxsize: int = 500):
        """مقداردهی اولیه صف.

        Args:
            maxsize: حداکثر تعداد آیتم‌های صف (پیش‌فرض: 500)
        """
        self.queue: asyncio.Queue[PublishItem | None] = asyncio.Queue(maxsize=maxsize)  # صف ناهمزمان
        self._running = False  # وضعیت اجرای consumer

    @classmethod
    def get_instance(cls) -> PublishQueue:
        """دریافت نمونه singleton صف.

        اگر نمونه‌ای وجود نداشته باشد، ایجاد می‌شود.

        Returns:
            نمونه یکتای PublishQueue
        """
        if cls._instance is None:  # اگر نمونه‌ای ساخته نشده
            cls._instance = PublishQueue()  # ساخت نمونه جدید
        return cls._instance  # بازگرداندن نمونه

    @classmethod
    def get(cls) -> PublishQueue:
        """دریافت نمونه singleton — نام مستعار برای backward compatibility.

        Returns:
            نمونه یکتای PublishQueue
        """
        return cls.get_instance()  # فراخوانی get_instance

    async def put(self, config: str, country_code: str = "UN") -> None:
        """اضافه کردن کانفیگ به صف انتشار.

        اگر صف پر باشد، صبر می‌کند تا جای خالی ایجاد شود.

        Args:
            config: متن کانفیگ V2Ray
            country_code: کد کشور دو حرفی (پیش‌فرض: UN)
        """
        await self.queue.put(PublishItem(config=config, country_code=country_code))  # افزودن به صف

    async def get_item(self) -> PublishItem | None:
        """دریافت و حذف آیتم بعدی از صف.

        اگر صف خالی باشد، صبر می‌کند تا آیتمی اضافه شود.
        None به معنای سیگنال توقف است.

        Returns:
            آیتم انتشار یا None (سیگنال توقف)
        """
        return await self.queue.get()  # دریافت آیتم از صف

    def task_done(self) -> None:
        """علامت‌گذاری پردازش آیتم فعلی — برای هماهنگی join()."""
        self.queue.task_done()  # اطلاع به صف که پردازش تمام شد

    async def stop(self) -> None:
        """ارسال سیگنال توقف به consumer.

        با اضافه کردن None به صف، consumer متوجه توقف می‌شود.
        """
        await self.queue.put(None)  # ارسال سیگنال توقف
