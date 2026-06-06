# app/handlers/admin.py — handlerهای ادمین (پنل، VIP، broadcast، clean IP)

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.menus_refactor import (
    admin_panel_menu,
    back as back_button,
    clean_ip_menu,
    main_menu,
    vip_panel_menu,
)
from app.middlewares.auth import is_admin, is_owner, require_admin
from core.logger import get_logger
from database import crud
from database.session import get_session_factory

logger = get_logger()


def _get_scraper_state(context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not hasattr(context.bot_data, "scraper_enabled"):
        context.bot_data["scraper_enabled"] = True
    return context.bot_data.get("scraper_enabled", True)


def scraper_is_enabled(context: ContextTypes.DEFAULT_TYPE | None = None) -> bool:
    if context is None:
        return True
    return _get_scraper_state(context)


def set_scraper_enabled(context: ContextTypes.DEFAULT_TYPE, value: bool) -> None:
    context.bot_data["scraper_enabled"] = value


async def _admin_menu_flag(user_id: int) -> bool:
    factory = get_session_factory()
    async with factory() as session:
        return await is_admin(session, user_id)


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """callbackهای ادمین. False = not handled."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    factory = get_session_factory()

    admin_routes = {
        "admin_panel", "add_admin", "admin_users", "admin_stats",
        "admin_broadcast", "vip_panel", "vip_add", "vip_remove",
        "vip_list", "vip_broadcast", "clean_ip_menu", "clean_ip_upload",
        "list_clean_ip", "scraper_status", "scraper_toggle",
        "ip_management_menu", "ip_single", "ip_bulk", "ip_file",
        "list_admins", "remove_admin",
    }
    if data not in admin_routes:
        return False

    async with factory() as session:
        if not await require_admin(session, user_id):
            await query.answer("⛔ دسترسی ندارید", show_alert=True)
            return True

    # ─── Admin panel ───
    if data == "admin_panel":
        await query.edit_message_text("🛠 پنل مدیریت", reply_markup=admin_panel_menu())
        return True

    if data == "add_admin":
        if not await is_owner(user_id):
            await query.answer("⛔ فقط مالک", show_alert=True)
            return True
        context.user_data["awaiting_admin_id"] = True
        await query.edit_message_text(
            "👤 آیدی عددی ادمین جدید را ارسال کنید:",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "admin_users":
        async with factory() as session:
            count = await crud.count_users(session)
        await query.edit_message_text(
            f"👥 تعداد کاربران: {count}",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "admin_stats":
        async with factory() as session:
            users = await crud.count_users(session)
            starts = await crud.total_starts(session)
        await query.edit_message_text(
            f"📊 آمار\n\n👥 کاربران: {users}\n🚀 استارت‌ها: {starts}",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "admin_broadcast":
        context.user_data["broadcast_mode"] = True
        await query.edit_message_text(
            "📢 پیام همگانی را ارسال کنید:",
            reply_markup=back_button("admin_panel"),
        )
        return True

    # ─── VIP ───
    if data == "vip_panel":
        await query.edit_message_text("⭐ پنل VIP", reply_markup=vip_panel_menu())
        return True

    if data == "vip_add":
        context.user_data["awaiting_vip_id"] = True
        await query.edit_message_text(
            "👤 آیدی VIP را ارسال کنید:",
            reply_markup=back_button("vip_panel"),
        )
        return True

    if data == "vip_remove":
        context.user_data["awaiting_vip_remove"] = True
        await query.edit_message_text(
            "❌ آیدی VIP برای حذف:",
            reply_markup=back_button("vip_panel"),
        )
        return True

    if data == "vip_list":
        async with factory() as session:
            vips = await crud.list_vips(session)
        if not vips:
            await query.edit_message_text("❌ VIP ثبت نشده.", reply_markup=back_button("vip_panel"))
            return True
        text = "⭐ لیست VIP\n\n"
        for i, vip in enumerate(vips[:50], 1):
            text += f"{i}. `{vip.user_id}` — {vip.added_at:%Y-%m-%d}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button("vip_panel"))
        return True

    if data == "vip_broadcast":
        context.user_data["vip_broadcast_mode"] = True
        await query.edit_message_text(
            "📢 پیام VIP را ارسال کنید:",
            reply_markup=back_button("vip_panel"),
        )
        return True

    # ─── Clean IP ───
    if data == "clean_ip_menu":
        await query.edit_message_text("🌐 مدیریت Clean IP", reply_markup=clean_ip_menu())
        return True

    if data == "clean_ip_upload":
        context.user_data["awaiting_clean_ip"] = True
        await query.edit_message_text(
            "📄 فایل txt آی‌پی‌ها را ارسال کنید:",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    if data == "list_clean_ip":
        async with factory() as session:
            count = await crud.count_clean_ips(session)
        await query.edit_message_text(
            f"🌐 تعداد Clean IP: {count}",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    # ─── Scraper control ───
    if data == "scraper_status":
        status = "🟢 فعال" if scraper_is_enabled(context) else "🔴 غیرفعال"
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تغییر وضعیت", callback_data="scraper_toggle")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")],
        ])
        await query.edit_message_text(f"Scraper: {status}", reply_markup=kb)
        return True

    if data == "scraper_toggle":
        set_scraper_enabled(context, not scraper_is_enabled(context))
        status = "🟢 فعال" if scraper_is_enabled(context) else "🔴 غیرفعال"
        await query.answer(f"Scraper {status}", show_alert=True)
        return True

    return False


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """متن‌های stateful ادمین."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    factory = get_session_factory()

    # ─── Add admin ───
    if context.user_data.get("awaiting_admin_id"):
        context.user_data.pop("awaiting_admin_id", None)
        if not await is_owner(user_id):
            await update.message.reply_text("⛔ فقط مالک", reply_markup=main_menu(True))
            return True
        try:
            new_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ آیدی نامعتبر", reply_markup=main_menu(True))
            return True
        async with factory() as session:
            added = await crud.add_admin(session, new_id, user_id)
        msg = "✅ ادمین اضافه شد" if added else "⚠️ از قبل ادمین بود"
        await update.message.reply_text(msg, reply_markup=main_menu(True))
        return True

    # ─── VIP add/remove ───
    if context.user_data.get("awaiting_vip_id"):
        context.user_data.pop("awaiting_vip_id", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("⛔ دسترسی ندارید")
                return True
        try:
            vip_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ آیدی نامعتبر", reply_markup=main_menu(True))
            return True
        async with factory() as session:
            await crud.add_vip(session, vip_id)
        await update.message.reply_text(f"✅ VIP {vip_id} اضافه شد", reply_markup=main_menu(True))
        return True

    if context.user_data.get("awaiting_vip_remove"):
        context.user_data.pop("awaiting_vip_remove", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                return True
        try:
            vip_id = int(text)
        except ValueError:
            await update.message.reply_text("❌ آیدی نامعتبر", reply_markup=main_menu(True))
            return True
        async with factory() as session:
            await crud.remove_vip(session, vip_id)
        await update.message.reply_text(f"✅ VIP {vip_id} حذف شد", reply_markup=main_menu(True))
        return True

    # ─── Broadcast ───
    if context.user_data.get("broadcast_mode"):
        context.user_data.pop("broadcast_mode", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("⛔ دسترسی ندارید")
                return True
            user_ids = await crud.get_all_user_ids(session)

        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await update.get_bot().send_message(chat_id=uid, text=text)
                sent += 1
            except Exception as exc:
                logger.error("Broadcast failed for user {}: {}", uid, exc)
                failed += 1

        msg = f"✅ ارسال به {sent} کاربر"
        if failed > 0:
            msg += f"\n⚠️ {failed} کاربر ارسال نشد"
        await update.message.reply_text(msg, reply_markup=main_menu(True))
        return True

    if context.user_data.get("vip_broadcast_mode"):
        context.user_data.pop("vip_broadcast_mode", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("⛔ دسترسی ندارید")
                return True
            vip_ids = await crud.get_vip_ids(session)

        sent = 0
        failed = 0
        for uid in vip_ids:
            try:
                await update.get_bot().send_message(chat_id=uid, text=text)
                sent += 1
            except Exception as exc:
                logger.error("VIP broadcast failed for user {}: {}", uid, exc)
                failed += 1

        msg = f"✅ ارسال به {sent} VIP"
        if failed > 0:
            msg += f"\n⚠️ {failed} VIP ارسال نشد"
        await update.message.reply_text(msg, reply_markup=main_menu(True))
        return True

    return False


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """آپلود فایل Clean IP."""
    if not context.user_data.get("awaiting_clean_ip"):
        return

    user_id = update.effective_user.id
    factory = get_session_factory()
    async with factory() as session:
        if not await require_admin(session, user_id):
            await update.message.reply_text("⛔ دسترسی ندارید")
            return

    document = update.message.document
    if not document or not document.file_name.endswith(".txt"):
        await update.message.reply_text("❌ فقط فایل .txt")
        return

    file = await document.get_file()
    from core.config import BASE_DIR
    dest_dir = BASE_DIR / "data" / "clean_ips"
    dest_dir.mkdir(parents=True, exist_ok=True)
    # جلوگیری از path traversal: فقط basename و محدودسازی کاراکترهای مجاز
    import re

    original_name = document.file_name
    safe_name = re.sub(r"[\\/]+", "_", original_name)
    safe_name = safe_name.replace("..", "")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    safe_name = safe_name[:120] if safe_name else "clean_ips.txt"
    if not safe_name.lower().endswith(".txt"):
        safe_name = safe_name + ".txt"

    dest = dest_dir / safe_name
    await file.download_to_drive(str(dest))

    count = 0
    invalid = 0
    async with factory() as session:
        await crud.delete_old_clean_ips(session)
        try:
            with open(dest, "r", encoding="utf-8") as f:
                for line in f:
                    ip = line.strip()
                    if not ip or ip.startswith("#"):
                        continue
                    if _is_valid_ip(ip):
                        await crud.add_clean_ip(session, ip)
                        count += 1
                    else:
                        invalid += 1
                        logger.warning("Invalid IP format: {}", ip)
        except Exception as exc:
            logger.error("Error reading clean IP file: {}", exc)
            await update.message.reply_text(f"❌ خطا در خواندن فایل: {exc}")
            context.user_data.pop("awaiting_clean_ip", None)
            return

    context.user_data.pop("awaiting_clean_ip", None)
    msg = f"✅ {count} IP ذخیره شد"
    if invalid > 0:
        msg += f"\n⚠️ {invalid} IP نامعتبر نادیده گرفته شد"
    await update.message.reply_text(msg, reply_markup=main_menu(True))


def _is_valid_ip(ip: str) -> bool:
    """تطابق IPv4 ساده."""
    import re
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip):
        return False
    parts = ip.split(".")
    return all(0 <= int(part) <= 255 for part in parts)


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    factory = get_session_factory()
    try:
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("⛔ دسترسی ندارید")
                return
            users = await crud.count_users(session)
            starts = await crud.total_starts(session)
        scraper = "🟢" if scraper_is_enabled(context) else "🔴"
        await update.message.reply_text(
            f"🟢 HEALTH OK\n👥 Users: {users}\n🚀 Starts: {starts}\nScraper: {scraper}"
        )
    except Exception as exc:
        logger.error("Health check failed: {}", exc)
        await update.message.reply_text(f"🔴 ERROR: {exc}")
