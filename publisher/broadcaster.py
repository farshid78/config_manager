# publisher/broadcaster.py
from __future__ import annotations

import asyncio
import html

import aiohttp

from constants import (
    PUBLISH_CONCURRENCY,
    PUBLISH_DELAY_SECONDS,
    PUBLISH_MAX_RETRIES,
)

from core.config import get_settings

from core.logger import get_logger
from publisher.queue import PublishQueue

logger = get_logger()

LINE = "━" * 20


class Broadcaster:

    _instance: Broadcaster | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.settings = get_settings()
        self.queue = PublishQueue.get()
        self._task: asyncio.Task | None = None

    async def send_message(self, text: str, session: aiohttp.ClientSession, retries: int = 0) -> bool:
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
                    return await self.send_message(text, session, retries + 1)
                if resp.status == 200:
                    return True
                body = await resp.text()
                logger.error("Publish failed | status={} body={}", resp.status, body)
                return False
        except (asyncio.TimeoutError, aiohttp.ClientError) as exc:
            logger.error("Send failed (retry {}/{}): {}", retries, PUBLISH_MAX_RETRIES, exc)
            if retries < PUBLISH_MAX_RETRIES:
                await asyncio.sleep(2)
                return await self.send_message(text, session, retries + 1)
            return False

    def format_message(self, config: str, country_code: str) -> str:
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
        footer = f"📢 <a href=\"https://t.me/{channel}\">t.me/{channel}</a>"

        return f"{header}\n{separator}\n{body}\n{separator}\n{footer}"

    async def worker(self, worker_id: int) -> None:
        logger.info("Broadcaster worker started | id={}", worker_id)
        async with aiohttp.ClientSession() as session:
            while True:
                item = await self.queue.get_item()
                if item is None:
                    self.queue.task_done()
                    break

                text = self.format_message(item.config, item.country_code)
                ok = await self.send_message(text, session)
                if ok:
                    logger.debug("Published config | country={} | worker={}", item.country_code, worker_id)

                self.queue.task_done()

                # در حالت concurrency، مکث ثابت فقط کمی اثر throttling دارد تا throughput کند نشود.
                await asyncio.sleep(PUBLISH_DELAY_SECONDS)

        logger.info("Broadcaster worker stopped | id={}", worker_id)


    def start(self) -> asyncio.Task:
        # ایجاد worker pool (concurrency محدود)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._start_workers())
        return self._task

    async def _start_workers(self) -> None:
        workers = []
        for i in range(PUBLISH_CONCURRENCY):
            workers.append(asyncio.create_task(self.worker(worker_id=i + 1)))
        try:
            await asyncio.gather(*workers)
        except asyncio.CancelledError:
            for t in workers:
                t.cancel()
            raise


    async def stop(self) -> None:
        await self.queue.stop()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
