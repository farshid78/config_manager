# app/bot/menus.py — منوهای Inline Keyboard

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from constants import COUNTRY_LABELS, PROTOCOLS


def main_menu(is_admin_user: bool = False) -> InlineKeyboardMarkup:
    """منوی اصلی کاربر — فقط Inline."""
    keyboard = [
        [
            InlineKeyboardButton("🌍 کشورها", callback_data="menu_country"),
            InlineKeyboardButton("⚙️ پروتکل", callback_data="menu_protocol"),
        ],
        [
            InlineKeyboardButton("📦 آخرین ۲۰", callback_data="last_20"),
            InlineKeyboardButton("🔢 دلخواه", callback_data="menu_custom"),
        ],
    ]
    if is_admin_user:
        keyboard.append([
            InlineKeyboardButton("👑 پنل ادمین", callback_data="admin_panel"),
        ])
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"),
    ])
    return InlineKeyboardMarkup(keyboard)


def country_menu() -> InlineKeyboardMarkup:
    """انتخاب کشور."""
    rows = []
    for code, label in COUNTRY_LABELS.items():
        rows.append([InlineKeyboardButton(label, callback_data=f"country_{code}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(rows)


def protocol_menu(back_callback: str = "back_main") -> InlineKeyboardMarkup:
    """انتخاب پروتکل."""
    labels = {
        "vless": "🔵 VLESS",
        "vmess": "🟡 VMESS",
        "trojan": "🟣 TROJAN",
        "shadowsocks": "⚫ SHADOWSOCKS",
    }
    rows = [
        [InlineKeyboardButton(labels[p], callback_data=f"proto_{p}")]
        for p in PROTOCOLS
    ]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def admin_panel_menu() -> InlineKeyboardMarkup:
    """پنل ادمین."""
    keyboard = [
        [InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin")],
        [InlineKeyboardButton("⭐ مدیریت VIP", callback_data="vip_panel")],
        [InlineKeyboardButton("👥 تعداد کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 ارسال همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🌐 Clean IP", callback_data="clean_ip_menu")],
        [InlineKeyboardButton("🔄 وضعیت Scraper", callback_data="scraper_status")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def vip_panel_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ افزودن VIP", callback_data="vip_add")],
        [InlineKeyboardButton("❌ حذف VIP", callback_data="vip_remove")],
        [InlineKeyboardButton("📋 لیست VIP", callback_data="vip_list")],
        [InlineKeyboardButton("📢 ارسال به VIP", callback_data="vip_broadcast")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def clean_ip_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📄 آپلود فایل txt", callback_data="clean_ip_upload")],
        [InlineKeyboardButton("📋 تعداد IPها", callback_data="list_clean_ip")],
        [InlineKeyboardButton("🌐 مدیریت IP پروکسی", callback_data="ip_management_menu")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def ip_management_menu() -> InlineKeyboardMarkup:
    """منوی مدیریت IP برای اعمال بر روی کانفیگ‌ها."""
    keyboard = [
        [InlineKeyboardButton("➕ IP تکی", callback_data="ip_single")],
        [InlineKeyboardButton("➕ لیست IP (متن)", callback_data="ip_bulk")],
        [InlineKeyboardButton("📤 Upload IP (txt)", callback_data="ip_file")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="clean_ip_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button(callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data=callback)],
    ])
