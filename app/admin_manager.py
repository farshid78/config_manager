from config.admin_store import load_admins, save_admins


def is_admin(user_id: int) -> bool:
    return user_id in load_admins()


def add_admin(user_id: int):
    admins = load_admins()
    admins.add(user_id)
    save_admins(admins)