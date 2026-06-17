# app/handlers/connection_monitor.py - مانیتور اتصال

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, Application

from core.logger import get_logger
from database.session import get_session_factory
from database.crud import update_connection_status

logger = get_logger()


class ConnectionMonitor:
    """مانیتور اتصال به اینترنت"""

    def __init__(self, application: Application):
        self.application = application
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self) -> None:
        """شروع مانیتورینگ اتصال"""
        if self._is_running:
            return

        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_connection())
        logger.info("Connection monitor started")

    async def stop(self) -> None:
        """توقف مانیتورینگ اتصال"""
        if not self._is_running:
            return

        self._is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Connection monitor stopped")

    async def _monitor_connection(self) -> None:
        """مانیتور کردن اتصال"""
        while self._is_running:
            try:
                # تست اتصال به اینترنت
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://httpbin.org/get", timeout=10) as response:
                        if response.status == 200:
                            await self._update_status(True)
                        else:
                            await self._update_status(False)

                # انتظار برای تست مجدد
                await asyncio.sleep(60)
            except Exception as exc:
                logger.error(f"Connection test failed: {exc}")
                await self._update_status(False)
                await asyncio.sleep(60)

    async def _update_status(self, is_connected: bool) -> None:
        """به‌روزرسانی وضعیت اتصال در دیتابیس"""
        try:
            factory = get_session_factory()
            async with factory() as session:
                await update_connection_status(session, is_connected)
                logger.debug(f"Connection status updated: {is_connected}")
        except Exception as exc:
            logger.error(f"Failed to update connection status: {exc}")
