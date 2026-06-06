# app/middlewares/auth.py — کنترل دسترسی owner/admin

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from database import crud


async def is_owner(user_id: int) -> bool:
    """مالک اصلی از .env."""
    return user_id == get_settings().owner_id


async def is_admin(session: AsyncSession, user_id: int) -> bool:
    """owner یا ادمین دیتابیس."""
    if await is_owner(user_id):
        return True
    admin_ids = await crud.get_admin_ids(session)
    return user_id in admin_ids


async def require_admin(session: AsyncSession, user_id: int) -> bool:
    return await is_admin(session, user_id)


async def require_owner(user_id: int) -> bool:
    return await is_owner(user_id)
