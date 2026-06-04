from config.config import settings
from config.admin_store import load_admins, save_admins


# 👑 OWNER CHECK
def is_owner(user_id: int) -> bool:
    return user_id == settings.OWNER_ID


# 👥 ADMIN CHECK (owner + dynamic admins)
def is_admin(user_id: int) -> bool:
    if user_id == settings.OWNER_ID:
        return True

    return user_id in load_admins()


# ➕ ADD ADMIN (فقط owner اجازه دارد)
def add_admin(user_id: int, new_admin_id: int) -> bool:
    if not is_owner(user_id):
        return False

    admins = load_admins()
    admins.add(new_admin_id)
    save_admins(admins)
    return True


# ❌ REMOVE ADMIN (اختیاری ولی حرفه‌ای)
def remove_admin(user_id: int, target_id: int) -> bool:
    if not is_owner(user_id):
        return False

    admins = load_admins()
    if target_id in admins:
        admins.remove(target_id)
        save_admins(admins)
        return True

    return False