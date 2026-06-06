# publisher/queue.py — صف async برای انتشار

from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class PublishItem:
    """یک آیتم در صف انتشار."""
    config: str
    country_code: str


class PublishQueue:
    """Singleton queue با backpressure."""

    _instance: PublishQueue | None = None

    def __init__(self, maxsize: int = 500):
        self.queue: asyncio.Queue[PublishItem | None] = asyncio.Queue(maxsize=maxsize)
        self._running = False

    @classmethod
    def get_instance(cls) -> PublishQueue:
        if cls._instance is None:
            cls._instance = PublishQueue()
        return cls._instance

    @classmethod
    def get(cls) -> PublishQueue:
        """برای backward compatibility."""
        return cls.get_instance()

    async def put(self, config: str, country_code: str = "UN") -> None:
        await self.queue.put(PublishItem(config=config, country_code=country_code))

    async def get_item(self) -> PublishItem | None:
        return await self.queue.get()

    def task_done(self) -> None:
        self.queue.task_done()

    async def stop(self) -> None:
        await self.queue.put(None)
