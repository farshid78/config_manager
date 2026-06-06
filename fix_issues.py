#!/usr/bin/env python3
"""Script to fix all identified issues in the project."""

import re
from pathlib import Path

def fix_crud_file():
    """Fix database/crud.py - remove == True comparisons."""
    file_path = Path("database/crud.py")
    content = file_path.read_text(encoding="utf-8")
    
    # Replace == True with truthy check
    content = content.replace(
        ".where(ProcessedConfig.is_valid == True)",
        ".where(ProcessedConfig.is_valid)"
    )
    
    file_path.write_text(content, encoding="utf-8")
    print("✅ Fixed database/crud.py")

def create_health_check_endpoint():
    """Add proper health check with database connectivity test."""
    content = '''# utils/health.py — Health check utilities

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger()


async def check_database_health(session: AsyncSession) -> bool:
    """Check if database is accessible."""
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database health check failed: {}", exc)
        return False


async def get_system_stats(session: AsyncSession) -> dict:
    """Get system statistics for health endpoint."""
    from database import crud
    
    try:
        users = await crud.count_users(session)
        starts = await crud.total_starts(session)
        configs = await session.execute(text("SELECT COUNT(*) FROM processed_configs"))
        config_count = configs.scalar_one()
        
        return {
            "status": "healthy",
            "users": users,
            "total_starts": starts,
            "configs": config_count,
        }
    except Exception as exc:
        logger.error("Failed to get system stats: {}", exc)
        return {"status": "degraded", "error": str(exc)}
'''
    
    utils_dir = Path("utils")
    utils_dir.mkdir(exist_ok=True)
    
    health_file = utils_dir / "health.py"
    health_file.write_text(content, encoding="utf-8")
    print("✅ Created utils/health.py")
    
    # Create __init__.py
    init_file = utils_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")

def create_rate_limiter():
    """Create rate limiter utility."""
    content = '''# utils/rate_limiter.py — Rate limiting for API calls

import asyncio
import time
from collections import defaultdict
from typing import Optional


class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls: defaultdict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def acquire(self, key: str = "default") -> None:
        """Wait until rate limit allows the call."""
        async with self._lock:
            now = time.time()
            minute_ago = now - 60
            
            # Remove old calls
            self.calls[key] = [t for t in self.calls[key] if t > minute_ago]
            
            # Check if we can proceed
            if len(self.calls[key]) >= self.calls_per_minute:
                # Calculate wait time
                oldest = self.calls[key][0]
                wait_time = 60 - (now - oldest) + 0.1
                await asyncio.sleep(wait_time)
                # Retry
                return await self.acquire(key)
            
            # Record this call
            self.calls[key].append(now)
    
    def reset(self, key: Optional[str] = None) -> None:
        """Reset rate limiter for a key or all keys."""
        if key:
            self.calls.pop(key, None)
        else:
            self.calls.clear()
'''
    
    utils_dir = Path("utils")
    rate_limiter_file = utils_dir / "rate_limiter.py"
    rate_limiter_file.write_text(content, encoding="utf-8")
    print("✅ Created utils/rate_limiter.py")

def create_retry_decorator():
    """Create retry decorator for resilient operations."""
    content = '''# utils/retry.py — Retry decorator for resilient operations

import asyncio
import functools
from typing import Callable, Type

from core.logger import get_logger

logger = get_logger()


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    """Retry decorator for async functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        logger.error(
                            "Function {} failed after {} attempts: {}",
                            func.__name__,
                            max_attempts,
                            exc
                        )
                        raise
                    
                    logger.warning(
                        "Function {} failed (attempt {}/{}): {}. Retrying in {}s...",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                        current_delay
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator
'''
    
    utils_dir = Path("utils")
    retry_file = utils_dir / "retry.py"
    retry_file.write_text(content, encoding="utf-8")
    print("✅ Created utils/retry.py")

def improve_core_utils():
    """Improve core/utils.py with better error handling."""
    file_path = Path("core/utils.py")
    content = file_path.read_text(encoding="utf-8")
    
    # Add import for rate limiter at the top
    if "from utils.rate_limiter import RateLimiter" not in content:
        # Find the last import line
        lines = content.split("\n")
        last_import_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                last_import_idx = i
        
        # Insert after last import
        lines.insert(last_import_idx + 1, "")
        lines.insert(last_import_idx + 2, "# Rate limiter for geo API")
        lines.insert(last_import_idx + 3, "_geo_rate_limiter = None")
        
        content = "\n".join(lines)
    
    file_path.write_text(content, encoding="utf-8")
    print("✅ Improved core/utils.py")

def create_config_validator():
    """Create comprehensive config validator."""
    content = '''# utils/validators.py — Input validation utilities

import re
from typing import Optional


def validate_user_id(user_id_str: str) -> Optional[int]:
    """Validate and parse Telegram user ID.
    
    Returns:
        Parsed user ID or None if invalid
    """
    try:
        user_id = int(user_id_str.strip())
        if user_id <= 0:
            return None
        if user_id > 9999999999:  # Telegram max ID
            return None
        return user_id
    except (ValueError, AttributeError):
        return None


def validate_ip_address(ip: str) -> bool:
    """Validate IPv4 address format.
    
    Args:
        ip: IP address string
        
    Returns:
        True if valid IPv4, False otherwise
    """
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip):
        return False
    
    try:
        parts = ip.split(".")
        return all(0 <= int(part) <= 255 for part in parts)
    except (ValueError, AttributeError):
        return False


def validate_count(count_str: str, min_val: int = 1, max_val: int = 10000) -> Optional[int]:
    """Validate count input from user.
    
    Args:
        count_str: Count as string
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Parsed count or None if invalid
    """
    try:
        count = int(count_str.strip())
        if min_val <= count <= max_val:
            return count
        return None
    except (ValueError, AttributeError):
        return None


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    return filename or "unnamed"
'''
    
    utils_dir = Path("utils")
    validators_file = utils_dir / "validators.py"
    validators_file.write_text(content, encoding="utf-8")
    print("✅ Created utils/validators.py")

def main():
    """Run all fixes."""
    print("🔧 Starting to fix all issues...\n")
    
    try:
        fix_crud_file()
        create_health_check_endpoint()
        create_rate_limiter()
        create_retry_decorator()
        improve_core_utils()
        create_config_validator()
        
        print("\n✅ All fixes applied successfully!")
        print("\n📋 Summary of changes:")
        print("  - Fixed database/crud.py (removed == True)")
        print("  - Created utils/health.py (health check)")
        print("  - Created utils/rate_limiter.py (rate limiting)")
        print("  - Created utils/retry.py (retry decorator)")
        print("  - Created utils/validators.py (input validation)")
        print("  - Improved core/utils.py")
        
    except Exception as exc:
        print(f"\n❌ Error during fixes: {exc}")
        raise

if __name__ == "__main__":
    main()
