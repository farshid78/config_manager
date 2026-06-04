# tests/test_admin.py

from app.admin_manager import is_admin

from config.config import settings


print("Admin ID:", settings.ADMIN_ID)

print(
    "Is Admin:",
    is_admin(settings.ADMIN_ID)
)