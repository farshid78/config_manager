# database/connection.py — Connection Pool, Auto-Reconnect, and Retry Logic
# Replaces single-point-of-failure patterns with resilient database connectivity

from __future__ import annotations

import asyncio
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from core.config import get_settings
from core.logger import get_logger

logger = get_logger()

# ─── Connection Pool Configuration ──────────────────────────

POOL_SIZE = 10           # Maximum connections in pool
POOL_OVERFLOW = 20       # Allow overflow beyond pool_size
POOL_RECYCLE_SECONDS = 3600  # Recycle connections every hour
POOL_TIMEOUT = 30        # Max seconds to wait for connection from pool
MAX_RETRIES = 3          # Max retry attempts on connection failure
RETRY_DELAY = 0.5        # Base delay between retries (seconds)


def create_engine() -> AsyncEngine:
    """Create SQLAlchemy async engine with connection pooling and pre-ping.

    - pool_pre_ping=True: validates connection before each use
    - pool_recycle: prevents stale connections
    - pool_size + max_overflow: handle concurrent load gracefully
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=POOL_OVERFLOW,
        pool_recycle=POOL_RECYCLE_SECONDS,
        pool_timeout=POOL_TIMEOUT,
    )
    logger.info(
        "DB engine created | url_type={} pool={}+{} timeout={}s",
        "postgres" if "postgres" in settings.database_url else "sqlite",
        POOL_SIZE,
        POOL_OVERFLOW,
        POOL_TIMEOUT,
    )
    return engine


async def check_connection(engine: AsyncEngine) -> bool:
    """Check if the database connection is alive.

    Returns True if the database responds, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return True
    except Exception as exc:
        logger.warning("DB connection check failed: {}", exc)
        return False


async def with_retry(func, *args, max_retries: int = MAX_RETRIES, **kwargs):
    """Execute an async database operation with automatic retry on connection errors.

    Implements exponential backoff with jitter for retries.
    Only retries on DisconnectionError and OperationalError (connection issues).

    Args:
        func: async callable to execute
        *args: positional args for func
        max_retries: max retry attempts
        **kwargs: keyword args for func

    Returns:
        Result of func(*args, **kwargs)

    Raises:
        The last exception if all retries fail
    """
    import random
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except (DisconnectionError, OperationalError) as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = RETRY_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
            logger.warning(
                "DB operation failed (attempt {}/{}): {} — retrying in {:.1f}s",
                attempt + 1,
                max_retries + 1,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
        except Exception:
            # Non-connection errors are not retried
            raise

    assert last_exc is not None
    logger.error("DB operation failed after {} retries", max_retries)
    raise last_exc
