from multiprocessing import context

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.query_service import QueryService
from database.database_manager import DatabaseManager
from services.file_builder import FileBuilder
from app.handlers.menus.main_menu import main_menu
from app.handlers.menus.country_menu import country_menu
from utils.protocol import detect_protocol
from config.admin_manager import is_admin


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data

    query_service = QueryService()
    file_builder = FileBuilder()

    # =========================
    # BACK MAIN
    # =========================
    if data == "back_main":
        context.user_data.clear()

        await query.edit_message_text(
            "🏠 منوی اصلی",
            reply_markup=main_menu(query.from_user.id)
        )
        return

    # =========================
    # COUNTRY MENU
    # =========================
    if data == "menu_country":
        await query.edit_message_text(
            "🌍 کشور مورد نظر را انتخاب کنید",
            reply_markup=country_menu()
        )
        return

    # =========================
    # LAST 10
    # =========================
    if data == "last_10":
        await query.edit_message_text("📦 در حال آماده سازی...")

        rows = query_service.get_last(10)
        file_path = file_builder.build_txt(rows, "last_10")

        await query.message.reply_document(
            document=open(file_path, "rb"),
            caption="📦 آخرین 10 کانفیگ"
        )

        await query.message.reply_text(
            "🏠 بازگشت به منوی اصلی",
            reply_markup=main_menu(query.from_user.id)
        )
        return

    # =========================
    # COUNTRY SELECT
    # =========================
    if data.startswith("country_"):
        country = data.replace("country_", "")
        context.user_data["country"] = country

        keyboard = [
            [InlineKeyboardButton("🔵 VLESS", callback_data="proto_vless")],
            [InlineKeyboardButton("🟡 VMESS", callback_data="proto_vmess")],
            [InlineKeyboardButton("🟣 TROJAN", callback_data="proto_trojan")],
            [InlineKeyboardButton("⚫ SHADOWSOCKS", callback_data="proto_shadowsocks")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]

        await query.edit_message_text(
            f"🌍 کشور: {country}\n⚙️ انتخاب پروتکل",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # =========================
    # PROTOCOL MENU
    # =========================
    if data == "menu_protocol":
        keyboard = [
            [InlineKeyboardButton("🔵 VLESS", callback_data="proto_vless")],
            [InlineKeyboardButton("🟡 VMESS", callback_data="proto_vmess")],
            [InlineKeyboardButton("🟣 TROJAN", callback_data="proto_trojan")],
            [InlineKeyboardButton("⚫ SHADOWSOCKS", callback_data="proto_shadowsocks")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")]
        ]

        await query.edit_message_text(
            "⚙️ پروتکل مورد نظر",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # =========================
    # FILTER
    # =========================
    if data.startswith("proto_"):
        proto = data.replace("proto_", "")
        country = context.user_data.get("country")

        await query.edit_message_text(f"⏳ فیلتر...\n🌍 {country or 'همه'} | ⚙️ {proto}")

        rows = query_service.get_last(1000)

        filtered = []
        for row in rows:
            config = row[0]
            detected_proto = detect_protocol(config)

            if detected_proto != proto:
                continue

            if country and len(row) > 1:
                if str(row[1]).lower() != country.lower():
                    continue

            filtered.append(row)

        file_path = file_builder.build_txt(filtered, f"{country or 'all'}_{proto}")

        await query.message.reply_document(
            document=open(file_path, "rb"),
            caption=f"📦 تعداد: {len(filtered)}"
        )

        await query.message.reply_text(
            "🏠 منوی اصلی",
            reply_markup=main_menu(query.from_user.id)
        )
        return

    # =========================
    # CUSTOM COUNT
    # =========================
    if data == "menu_custom":
        context.user_data["awaiting_count"] = True

        await query.edit_message_text("🔢 تعداد مورد نظر را ارسال کنید")
        return

    # =========================
    # ADMIN PANEL
    # =========================
    if data == "admin_panel":

        if not is_admin(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید",
                show_alert=True
            )
            return

        keyboard = [
            [InlineKeyboardButton(
                "➕ افزودن ادمین",
                callback_data="add_admin"
            )],

            [InlineKeyboardButton(
                "⭐ مدیریت VIP",
                callback_data="vip_panel"
            )],

            [InlineKeyboardButton(
                "👥 تعداد کاربران",
                callback_data="admin_users"
            )],

            [InlineKeyboardButton(
                "📊 آمار ربات",
                callback_data="admin_stats"
            )],

            [InlineKeyboardButton(
                "📢 ارسال همگانی",
                callback_data="admin_broadcast"
            )],

            [InlineKeyboardButton(
                "🔙 بازگشت",
                callback_data="back_main"
            )],

            [InlineKeyboardButton(
                "🌐 آپلود Clean IP",
                callback_data="clean_ip_upload"
            )],
        ]

        await query.edit_message_text(
            "🛠 پنل مدیریت",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # =========================
    # ADD ADMIN
    # =========================
    if data == "add_admin":

        if not is_admin(query.from_user.id):
            await query.answer("⛔ دسترسی ندارید", show_alert=True)
            return

        context.user_data["awaiting_admin_id"] = True

        await query.edit_message_text(
            "👤 آیدی عددی ادمین جدید را ارسال کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ])
        )
        return


    # =========================
    # USERS COUNT
    # =========================
    if data == "admin_users":

        if not is_admin(query.from_user.id):
            await query.answer("⛔ دسترسی ندارید", show_alert=True)
            return

        db = DatabaseManager()
        count = db.get_users_count()

        await query.edit_message_text(
            f"👥 تعداد کاربران: {count}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ])
        )
        return


    # =========================
    # STATS
    # =========================
    if data == "admin_stats":

        if not is_admin(query.from_user.id):
            await query.answer("⛔ دسترسی ندارید", show_alert=True)
            return

        db = DatabaseManager()

        await query.edit_message_text(
            f"📊 آمار\n\n"
            f"👥 کاربران: {db.get_users_count()}\n"
            f"🚀 استارت‌ها: {db.get_total_starts()}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ])
        )
        return


    # =========================
    # BROADCAST
    # =========================
    if data == "admin_broadcast":

        if not is_admin(query.from_user.id):
            await query.answer("⛔ دسترسی ندارید", show_alert=True)
            return

        context.user_data["broadcast_mode"] = True

        await query.edit_message_text(
            "📢 پیام همگانی را ارسال کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
            ])
        )
        return

    # =========================
    # CLEAN IP UPLOAD
    # =========================
    if data == "clean_ip_upload":

        if not is_admin(query.from_user.id):

            await query.answer(
                "⛔ دسترسی ندارید",
                show_alert=True
            )
            return

        context.user_data["awaiting_clean_ip"] = True

        await query.edit_message_text(
            "📄 فایل txt آیپی‌های تمیز را ارسال کنید"
        )
        return

    # =========================
    # VIP PANEL
    # =========================
    if data == "vip_panel":

        if not is_admin(query.from_user.id):
            await query.answer("⛔ دسترسی ندارید", show_alert=True)
            return

        keyboard = [
            [InlineKeyboardButton("➕ افزودن VIP", callback_data="vip_add")],
            [InlineKeyboardButton("❌ حذف VIP", callback_data="vip_remove")],
            [InlineKeyboardButton("📋 لیست VIP", callback_data="vip_list")],
            [InlineKeyboardButton("📢 ارسال به VIP", callback_data="vip_broadcast")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]

        await query.edit_message_text(
            "⭐ پنل مدیریت VIP",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # =========================
    # VIP LIST
    # =========================
    if data == "vip_list":

        if not is_admin(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید",
                show_alert=True
            )
            return

        db = DatabaseManager()

        vips = db.get_all_vips()

        if not vips:

            await query.edit_message_text(
                "❌ هیچ کاربر VIP ثبت نشده است",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "🔙 بازگشت",
                            callback_data="vip_panel"
                        )
                    ]
                ])
            )

            return

        text = "⭐ لیست کاربران VIP\n\n"

        for index, row in enumerate(vips[:50], start=1):

            user_id = row[0]

            if len(row) > 1:
                added_at = row[1]
            else:
                added_at = "-"

            text += (
                f"{index}. "
                f"`{user_id}`\n"
                f"📅 {added_at}\n\n"
            )

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="vip_panel"
                    )
                ]
            ])
        )

        return

    # =========================
    # VIP ADD
    # =========================
    if data == "vip_add":

        if not is_admin(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید",
                show_alert=True
            )
            return

        context.user_data["awaiting_vip_id"] = True
        context.user_data.pop("awaiting_vip_remove", None)
        await query.edit_message_text(
            "👤 آیدی عددی کاربر VIP را ارسال کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="vip_panel"
                )]
            ])
        )
        return

    # =========================
    # VIP REMOVE
    # =========================
    if data == "vip_remove":

        if not is_admin(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید",
                show_alert=True
            )
            return

        context.user_data.pop("awaiting_vip_id", None)
        context.user_data["awaiting_vip_remove"] = True

        await query.edit_message_text(
            "❌ آیدی کاربر VIP را ارسال کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="vip_panel"
                )]
            ])
        )

        return

    # =========================
    # VIP BROADCAST
    # =========================
    if data == "vip_broadcast":

        if not is_admin(query.from_user.id):
            await query.answer(
                "⛔ دسترسی ندارید",
                show_alert=True
            )
            return

        context.user_data["vip_broadcast_mode"] = True

        await query.edit_message_text(
            "📢 پیام برای کاربران VIP را ارسال کنید",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="vip_panel"
                )]
            ])
        )
        return

    # =========================
    # HANDLE CLEAN IP MENU
    # =========================
    if data == "clean_ip_menu":

        keyboard = [

            [
                InlineKeyboardButton(
                    "➕ افزودن IP",
                    callback_data="add_clean_ip"
                )
            ],

            [
                InlineKeyboardButton(
                    "📋 لیست IP ها",
                    callback_data="list_clean_ip"
                )
            ],

            [
                InlineKeyboardButton(
                    "⚙️ ساخت کانفیگ",
                    callback_data="build_clean_configs"
                )
            ],

            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="back_main"
                )
            ]
        ]

        await query.edit_message_text(
            "🧹 مدیریت IP های تمیز",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # =========================
    # CLEAN IP UPLOAD
    # =========================
    if data == "add_clean_ip":

        context.user_data["awaiting_clean_ip"] = True

        await query.edit_message_text(
            "📄 فایل txt آیپی‌ها را ارسال کنید"
        )

        return

    # =========================
    # CLEAN IP LIST
    # =========================
    if data == "list_clean_ip":

        db = DatabaseManager()

        count = db.get_clean_ip_count()

        await query.edit_message_text(
            f"🌐 تعداد Clean IP ها:\n\n{count}",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 بازگشت",
                        callback_data="clean_ip_menu"
                    )
                ]
            ])
        )

        return

    # =========================
    # BUILD CONFIGS
    # =========================
    if data == "build_clean_configs":

        await query.edit_message_text(
            "⚙️ در نسخه بعدی ساخته می‌شود"
        )

        return