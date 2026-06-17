# services/publisher_service.py — سرویس مستقل نشر
# این سرویس مسئولیت انتشار کانفیگ‌ها در کانال تلگرام را دارد

import asyncio
import html

import aiohttp

from constants import (
    PUBLISH_BATCH_PAUSE_SECONDS,
    PUBLISH_BATCH_SIZE,
    PUBLISH_DELAY_SECONDS,
    PUBLISH_MAX_RETRIES,
)
from core.config import get_settings
from core.logger import get_logger
from publisher.queue import PublishQueue

logger = get_logger()

LINE = "━" * 20


class PublisherService:
    """سرویس مستقل نشر کانفیگ‌ها.

    این سرویس مسئولیت‌های زیر را بر عهده دارد:
    - دریافت کانفیگ‌ها از صف
    - فرمت‌بندی کانفیگ‌ها برای انتشار
    - ارسال کانفیگ‌ها به کانال تلگرام
    - مدیریت خطاها و تلاش مجدد
    """

    def __init__(self):
        """مقداردهی اولیه سرویس نشر."""
        self.settings = get_settings()
        self.queue = PublishQueue.get()
        self._task = None
        self._running = False

    async def start(self) -> None:
        """راه‌اندازی سرویس نشر."""
        logger.info("Starting publisher service ...")
        self._running = True
        self._task = asyncio.create_task(self._worker())
        logger.info("Publisher service started")

    async def stop(self) -> None:
        """توقف سرویس نشر."""
        self._running = False
        await self.queue.stop()

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        logger.info("Publisher service stopped")

    async def _worker(self) -> None:
        """وظیفه اصلی نشر کانفیگ‌ها.

        این تابع به صورت دائمی در حال اجراست:
        1. دریافت کانفیگ از صف
        2. فرمت‌بندی کانفیگ
        3. ارسال به کانال تلگرام
        4. مدیریت تلاش مجدد در صورت خطا
        """
        logger.info("Publisher worker started")
        async with aiohttp.ClientSession() as session:
            batch_count = 0
            while self._running:
                item = await self.queue.get_item()
                if item is None:
                    self.queue.task_done()
                    break

                try:
                    text = self._format_message(item.config, item.country_code)
                    ok = await self._send_message(text, session)
                    if ok:
                        logger.debug("Published config | country={}", item.country_code)
                    else:
                        logger.warning("Failed to publish config | country={}", item.country_code)
                except Exception as exc:
                    logger.error("Error publishing config: {}", exc)

                self.queue.task_done()
                batch_count += 1

                await asyncio.sleep(PUBLISH_DELAY_SECONDS)

                if batch_count >= PUBLISH_BATCH_SIZE:
                    batch_count = 0
                    await asyncio.sleep(PUBLISH_BATCH_PAUSE_SECONDS)

        logger.info("Publisher worker stopped")

    async def _send_message(self, text: str, session: aiohttp.ClientSession, retries: int = 0) -> bool:
        """ارسال پیام به کانال تلگرام.

        Args:
            text: متن پیام
            session: نشست HTTP
            retries: تعداد تلاش‌های قبلی

        Returns:
            آیا ارسال با موفقیت انجام شد
        """
        url = f"https://api.telegram.org/bot{self.settings.bot_token}/sendMessage"
        proxy = self.settings.scraper_proxy.strip() if self.settings.scraper_proxy else None
        payload = {
            "chat_id": self.settings.channel_username,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            async with session.post(url, data=payload, proxy=proxy, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 429 and retries < PUBLISH_MAX_RETRIES:
                    data = await resp.json()
                    retry_after = data.get("parameters", {}).get("retry_after", 5)
                    logger.warning("Rate limit | sleep {}s", retry_after)
                    await asyncio.sleep(retry_after)
                    return await self._send_message(text, session, retries + 1)
                if resp.status == 200:
                    return True
                body = await resp.text()
                logger.error("Publish failed | status={} body={}", resp.status, body)
                return False
        except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
            logger.error("Send failed (retry {}/{}): {}", retries, PUBLISH_MAX_RETRIES, exc)
            if retries < PUBLISH_MAX_RETRIES:
                await asyncio.sleep(2)
                return await self._send_message(text, session, retries + 1)
            return False

    def _format_message(self, config: str, country_code: str) -> str:
        """فرمت‌بندی کانفیگ برای انتشار در کانال.

        Args:
            config: متن کانفیگ
            country_code: کد کشور

        Returns:
            متن فرمت‌بده شده برای انتشار
        """
        from constants import COUNTRY_LABELS
        from core.utils import get_flag, detect_protocol

        safe = html.escape(config)
        flag = get_flag(country_code)
        country_name = COUNTRY_LABELS.get(country_code, country_code)
        protocol = detect_protocol(config).upper()
        channel = self.settings.channel_username.lstrip("@")

        header = f"{flag} <b>{country_name}</b> ┃ ⚙️ {protocol}"
        separator = LINE
        body = f"<pre>{safe}</pre>"
        footer = f"📢 <a href="https://t.me/{channel}">t.me/{channel}</a>"

        return f"{header}\n{separator}\n{body}\n{separator}\n{footer}"

    async def get_queue_size(self) -> int:
        """دریافت اندازه فعلی صف نشر.

        Returns:
            تعداد کانفیگ‌های در صف منتظر انتشار
        """
        return self.queue.queue.qsize()

    async def get_stats(self) -> dict:
        """دریافت آمار سرویس نشر.

        Returns:
            دیکشنری حاوی آمار سرویس نشر
        """
        try:
            from database import crud
            from database.session import get_session_factory

            factory = get_session_factory()
            async with factory() as session:
                total_configs = await crud.count_processed_configs(session)
                latest_configs = await crud.get_latest_configs(session, limit=10)

                return {
                    "queue_size": await self.get_queue_size(),
                    "total_configs": total_configs,
                    "latest_configs": [
                        {
                            "id": config.id,
                            "country_code": config.country_code,
                            "protocol": config.protocol,
                            "host": config.host,
                            "source": config.source,
                            "created_at": config.created_at,
                        }
                        for config in latest_configs
                    ],
                }
        except Exception as exc:
            logger.error("Failed to get publisher stats: {}", exc)
            return {"queue_size": 0, "total_configs": 0, "latest_configs": []}
