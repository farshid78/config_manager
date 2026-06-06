# app/bot/menus_refactor.py — منوهای بازنویسی‌شده (امن، هماهنگ با callbackها)

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from constants import COUNTRY_LABELS, PROTOCOLS


def back(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=callback_data)]])


def main_menu(is_admin_user: bool = False) -> InlineKeyboardMarkup:
    keyboard: list[list[InlineKeyboardButton]] = [
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
        keyboard.append([InlineKeyboardButton("👑 ادمین", callback_data="admin_panel")])

    keyboard.append([InlineKeyboardButton("🔙", callback_data="back_main")])
    return InlineKeyboardMarkup(keyboard)


def country_menu(back_callback: str = "back_main") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(label, callback_data=f"country_{code}")]
        for code, label in COUNTRY_LABELS.items()
    ]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def protocol_menu(back_callback: str = "menu_country") -> InlineKeyboardMarkup:
    labels = {
        "vless": "🔵 VLESS",
        "vmess": "🟡 VMESS",
        "trojan": "🟣 TROJAN",
        "shadowsocks": "⚫ SHADOWSOCKS",
    }

    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(labels[p], callback_data=f"proto_{p}")]
        for p in PROTOCOLS
    ]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def admin_panel_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin")],
            [InlineKeyboardButton("⭐ VIP", callback_data="vip_panel")],
            [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 ارسال همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🌐 Clean IP", callback_data="clean_ip_menu")],
            [InlineKeyboardButton("🛠 Scraper", callback_data="scraper_status")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ]
    )


def vip_panel_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ افزودن VIP", callback_data="vip_add")],
            [InlineKeyboardButton("❌ حذف VIP", callback_data="vip_remove")],
            [InlineKeyboardButton("📋 لیست VIP", callback_data="vip_list")],
            [InlineKeyboardButton("📢 ارسال به VIP", callback_data="vip_broadcast")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
        ]
    )


def clean_ip_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📄 آپلود فایل txt", callback_data="clean_ip_upload")],
            [InlineKeyboardButton("📋 تعداد IPها", callback_data="list_clean_ip")],
            [InlineKeyboardButton("🧰 مدیریت IP پروکسی", callback_data="ip_management_menu")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
        ]
    )


def ip_management_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ IP تکی", callback_data="ip_single")],
            [InlineKeyboardButton("➕ لیست IP (متن)", callback_data="ip_bulk")],
            [InlineKeyboardButton("📤 Upload IP (txt)", callback_data="ip_file")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="clean_ip_menu")],
        ]
    )

