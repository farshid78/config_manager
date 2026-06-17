# app/bot/menus_refactor.py — منوهای حرفه‌ای Inline Keyboard
# تمام منوها با متن فارسی و راهنمای استفاده

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from constants import COUNTRY_LABELS, PROTOCOLS


def back(callback_data: str) -> InlineKeyboardMarkup:
    """دکمه بازگشت."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data=callback_data)]
    ])


def main_menu(is_admin_user: bool = False) -> InlineKeyboardMarkup:
    """منوی اصلی ربات."""
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
        keyboard.append([
            InlineKeyboardButton("👑 پنل مدیریت", callback_data="admin_panel"),
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="back_main"),
    ])
    return InlineKeyboardMarkup(keyboard)


def country_menu(back_callback: str = "back_main") -> InlineKeyboardMarkup:
    """منوی انتخاب کشور."""
    rows: list[list[InlineKeyboardButton]] = []

    items = list(COUNTRY_LABELS.items())
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"country_{items[i][0]}")]
        if i + 1 < len(items):
            row.append(
                InlineKeyboardButton(items[i + 1][1], callback_data=f"country_{items[i + 1][0]}")
            )
        rows.append(row)

    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def protocol_menu(back_callback: str = "menu_country") -> InlineKeyboardMarkup:
    """منوی انتخاب پروتکل."""
    labels = {
        "vless": "🔵 VLESS",
        "vmess": "🟡 VMESS",
        "trojan": "🟣 TROJAN",
        "shadowsocks": "⚫ SHADOWSOCKS",
    }

    rows: list[list[InlineKeyboardButton]] = []
    items = list(PROTOCOLS)
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(labels[items[i]], callback_data=f"proto_{items[i]}")]
        if i + 1 < len(items):
            row.append(
                InlineKeyboardButton(labels[items[i + 1]], callback_data=f"proto_{items[i + 1]}")
            )
        rows.append(row)

    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(rows)


def admin_panel_menu() -> InlineKeyboardMarkup:
    """پنل مدیریت ادمین."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin"),
            InlineKeyboardButton("❌ حذف ادمین", callback_data="remove_admin"),
        ],
        [
            InlineKeyboardButton("📋 لیست ادمین‌ها", callback_data="list_admins"),
            InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("📢 ارسال همگانی", callback_data="admin_broadcast"),
            InlineKeyboardButton("⭐ مدیریت VIP", callback_data="vip_panel"),
        ],
        [
            InlineKeyboardButton("🌐 Clean IP", callback_data="clean_ip_menu"),
            InlineKeyboardButton("🔧 مدیریت اسکرپر", callback_data="scraper_menu"),
        ],
        [
            InlineKeyboardButton("🔍 کانفیگ‌های سفید", callback_data="white_configs_menu"),
            InlineKeyboardButton("💊 سلامت سیستم", callback_data="health_check"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])


def vip_panel_menu() -> InlineKeyboardMarkup:
    """پنل مدیریت VIP."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ افزودن VIP", callback_data="vip_add"),
            InlineKeyboardButton("❌ حذف VIP", callback_data="vip_remove"),
        ],
        [
            InlineKeyboardButton("📋 لیست VIP", callback_data="vip_list"),
            InlineKeyboardButton("📢 ارسال به VIP", callback_data="vip_broadcast"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
    ])


def clean_ip_menu() -> InlineKeyboardMarkup:
    """منوی مدیریت Clean IP."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ IP تکی", callback_data="ip_single"),
            InlineKeyboardButton("📝 لیست IP", callback_data="ip_bulk"),
        ],
        [
            InlineKeyboardButton("📤 آپلود فایل txt", callback_data="ip_file"),
            InlineKeyboardButton("📋 تعداد IPها", callback_data="list_clean_ip"),
        ],
        [
            InlineKeyboardButton("⚙️ تنظیم تعداد کانفیگ", callback_data="ip_config_count"),
            InlineKeyboardButton("📊 کانفیگ‌های ساخته شده", callback_data="ip_generated_configs"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
    ])


def scraper_management_menu(is_enabled: bool) -> InlineKeyboardMarkup:
    """منوی مدیریت کامل اسکرپر."""
    toggle_label = "⏸ غیرفعال‌سازی" if is_enabled else "▶️ فعال‌سازی"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(toggle_label, callback_data="scraper_toggle"),
            InlineKeyboardButton("🔄 وضعیت", callback_data="scraper_status"),
        ],
        [
            InlineKeyboardButton("➕ افزودن کانال تلگرام", callback_data="scraper_add_tg"),
        ],
        [
            InlineKeyboardButton("➕ افزودن لینک اشتراک", callback_data="scraper_add_sub"),
        ],
        [
            InlineKeyboardButton("❌ حذف منبع", callback_data="scraper_remove"),
        ],
        [
            InlineKeyboardButton("📋 لیست منابع", callback_data="scraper_list"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
    ])


def scraper_menu() -> InlineKeyboardMarkup:
    """منوی مدیریت اسکرپر."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ افزودن کانال تلگرام", callback_data="scraper_add_tg"),
            InlineKeyboardButton("➕ افزودن لینک اشتراک", callback_data="scraper_add_sub"),
        ],
        [
            InlineKeyboardButton("📋 لیست منابع", callback_data="scraper_list"),
            InlineKeyboardButton("❌ حذف منبع", callback_data="scraper_remove"),
        ],
        [
            InlineKeyboardButton("🔄 وضعیت", callback_data="scraper_status"),
            InlineKeyboardButton("⏸/▶️ تغییر وضعیت", callback_data="scraper_toggle"),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
    ])


def confirm_menu(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """منوی تأیید."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ بله", callback_data=yes_data),
            InlineKeyboardButton("❌ خیر", callback_data=no_data),
        ],
    ])


def white_configs_menu() -> InlineKeyboardMarkup:
    """منوی کانفیگ‌های سفید."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚡ درخواست تست عملکرد (Alive/TTFB/Scoring)",
                callback_data="request_white_configs_perf",
            ),
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
    ])

