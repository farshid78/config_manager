# services/error_handler.py — مدیریت خطاها در سرویس‌ها

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.logger import get_logger

logger = get_logger()


class ErrorType(Enum):
    """انواع خطاها در سیستم."""
    DATABASE = "database"
    NETWORK = "network"
    VALIDATION = "validation"
    PARSING = "parsing"
    PUBLISHING = "publishing"
    SCRAPING = "scraping"
    UNKNOWN = "unknown"


class ErrorHandler:
    """مدیریت خطاها و ثبت لاگ‌ها."""

    def __init__(self):
        self._error_handlers: Dict[ErrorType, List[Callable]] = {
            error_type: [] for error_type in ErrorType
        }

    def register_handler(self, error_type: ErrorType, handler: Callable) -> None:
        """ثبت یک هندلر خطا."""
        self._error_handlers[error_type].append(handler)

    async def handle_error(self, error_type: ErrorType, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """پردازش یک خطا."""
        error_msg = f"Error occurred: {error_type.value} - {str(error)}"
        if context:
            error_msg += f" | Context: {context}"

        logger.error(error_msg)

        # اجرای هندلرهای ثبت‌شده
        for handler in self._error_handlers[error_type]:
            try:
                await handler(error, context)
            except Exception as handler_exc:
                logger.error(f"Error handler failed: {handler_exc}")


# نمونه singleton
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """دریافت نمونه singleton از ErrorHandler."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
