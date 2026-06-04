# app/admin_manager.py

from config.config import settings


def is_admin(user_id: int) -> bool:
    """
    بررسی ادمین بودن کاربر
    """

    return user_id == settings.ADMIN_ID