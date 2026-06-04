from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.admin_manager import is_admin


def main_menu(user_id=None):

    keyboard = [
        [
            InlineKeyboardButton("🌍 کشورها", callback_data="menu_country"),
            InlineKeyboardButton("⚙️ پروتکل", callback_data="menu_protocol")
        ],
        [
            InlineKeyboardButton("📦 آخرین 10", callback_data="last_10"),
            InlineKeyboardButton("🔢 دلخواه", callback_data="menu_custom")
        ]
    ]

    # فقط ادمین‌ها ببینن
    if user_id and is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton(
                "👑 پنل ادمین",
                callback_data="admin_panel"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")
    ])

    return InlineKeyboardMarkup(keyboard)