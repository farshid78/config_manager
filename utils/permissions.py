from config.admin_store import load_admins

def is_admin(user_id: int) -> bool:
    admins = load_admins()
    return user_id in admins