from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def country_menu():

    keyboard = [
        [InlineKeyboardButton("🇮🇷 Iran", callback_data="country_IR")],
        [InlineKeyboardButton("🇺🇸 USA", callback_data="country_US")],
        [InlineKeyboardButton("🇩🇪 Germany", callback_data="country_DE")],
        [InlineKeyboardButton("🇳🇱 Netherlands", callback_data="country_NL")],
        [InlineKeyboardButton("🇦🇪 UAE", callback_data="country_AE")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]

    return InlineKeyboardMarkup(keyboard)