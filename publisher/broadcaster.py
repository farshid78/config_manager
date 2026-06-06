# publisher/broadcaster.py — انتشار async در کانال با flood control

from __future__ import annotations

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


class Broadcaster:
    """Worker انتشار — از صف می‌خواند و به کانال می‌فرستد."""

    def __init__(self):
        self.settings = get_settings()
        self.queue = PublishQueue.get()
        self._task: asyncio.Task | None = None

    async def send_message(self, text: str, session: aiohttp.ClientSession, retries: int = 0) -> bool:
        url = f"https://api.telegram.org/bot{self.settings.bot_token}/sendMessage"
        payload = {
            "chat_id": self.settings.channel_username,
            "text": text,
            "parse_mode": "HTML",
        }
        async with session.post(url, data=payload) as resp:
            if resp.status == 429 and retries < PUBLISH_MAX_RETRIES:
                data = await resp.json()
                retry_after = data.get("parameters", {}).get("retry_after", 5)
                logger.warning("Rate limit | sleep {}s", retry_after)
                await asyncio.sleep(retry_after)
                return await self.send_message(text, session, retries + 1)
            if resp.status == 200:
                return True
            body = await resp.text()
            logger.error("Publish failed | status={} body={}", resp.status, body)
            return False

    def format_message(self, config: str, country_code: str) -> str:
        safe = html.escape(config)
        return (
            f"🔥 NEW CONFIG\n"
            f"📦 Category: {country_code}\n\n"
            f"<pre>{safe}</pre>"
        )

    async def worker(self) -> None:
        """حلقه worker — تا stop signal."""
        logger.info("Broadcaster worker started")
        async with aiohttp.ClientSession() as session:
            batch_count = 0
            while True:
                item = await self.queue.get()
                if item is None:
                    self.queue.task_done()
                    break

                text = self.format_message(item.config, item.country_code)
                ok = await self.send_message(text, session)
                if ok:
                    logger.debug("Published config | country={}", item.country_code)

                self.queue.task_done()
                batch_count += 1

                await asyncio.sleep(PUBLISH_DELAY_SECONDS)

                if batch_count >= PUBLISH_BATCH_SIZE:
                    batch_count = 0
                    await asyncio.sleep(PUBLISH_BATCH_PAUSE_SECONDS)

        logger.info("Broadcaster worker stopped")

    def start(self) -> asyncio.Task:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.worker())
        return self._task

    async def stop(self) -> None:
        await self.queue.stop()
        if self._task:
            await self._task
