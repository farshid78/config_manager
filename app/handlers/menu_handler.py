from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():

    keyboard = [
        [InlineKeyboardButton("🌍 کانفیگ بر اساس کشور", callback_data="menu_country")],
        [InlineKeyboardButton("📦 10 کانفیگ آخر", callback_data="last_10")],
        [InlineKeyboardButton("⚙️ بر اساس پروتکل", callback_data="menu_protocol")],
        [InlineKeyboardButton("🔢 دریافت دلخواه", callback_data="menu_custom")]
    ]

    return InlineKeyboardMarkup(keyboard)