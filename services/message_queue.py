# services/message_queue.py — صف پیام‌ها بین سرویس‌ها

from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Callable, Dict, Optional

from core.logger import get_logger

logger = get_logger()


class MessageType(Enum):
    """انواع پیام‌های بین سرویس‌ها."""
    CONFIG_SCRAPED = "config_scraped"
    CONFIG_VALIDATED = "config_validated"
    CONFIG_PUBLISHED = "config_published"
    ERROR_OCCURRED = "error_occurred"
    USER_ACTION = "user_action"


class MessageQueue:
    """صف پیام‌های بین سرویس‌ها."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: Dict[MessageType, list[Callable]] = {
            msg_type: [] for msg_type in MessageType
        }

    async def put(self, msg_type: MessageType, data: Dict[str, Any]) -> None:
        """افزودن پیام به صف."""
        await self._queue.put((msg_type, data))

    async def get(self) -> tuple[MessageType, Dict[str, Any]]:
        """دریافت پیام از صف."""
        return await self._queue.get()

    def subscribe(self, msg_type: MessageType, callback: Callable) -> None:
        """اشتراک در پیام‌های از نوع مشخص."""
        self._subscribers[msg_type].append(callback)

    async def process_messages(self) -> None:
        """پردازش پیام‌ها در صف."""
        while True:
            try:
                msg_type, data = await self.get()
                logger.debug(f"Processing message: {msg_type.value}")

                # ارسال به مشترکین
                for callback in self._subscribers[msg_type]:
                    try:
                        await callback(data)
                    except Exception as exc:
                        logger.error(f"Message callback error: {exc}")

            except Exception as exc:
                logger.error(f"Message processing error: {exc}")

    def start_processing(self) -> asyncio.Task:
        """شروع پردازش پیام‌ها."""
        return asyncio.create_task(self.process_messages())


# نمونه singleton
_message_queue = None


def get_message_queue() -> MessageQueue:
    """دریافت نمونه singleton از MessageQueue."""
    global _message_queue
    if _message_queue is None:
        _message_queue = MessageQueue()
    return _message_queue
