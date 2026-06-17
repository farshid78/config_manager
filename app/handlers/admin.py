# app/handlers/admin.py — handlerهای ادمین (پنل، VIP، broadcast، Clean IP، اسکرپر)

from __future__ import annotations

import asyncio
import ipaddress
from datetime import datetime, timedelta
from sqlalchemy import and_, desc, select

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from app.bot.menus_refactor import (
    admin_panel_menu,
    back as back_button,
    clean_ip_menu,
    main_menu,
    scraper_management_menu,
    scraper_menu,
    vip_panel_menu,
    white_configs_menu,
)
from app.middlewares.auth import is_admin, is_owner, require_admin
from constants import BROADCAST_DELAY_SECONDS
from core.logger import get_logger
from core.utils import generate_config
from database import crud
from database.models import CleanIP, ProcessedConfig
from database.session import get_session_factory

logger = get_logger()


# ─── توابع کمکی ────────────────────────────────────────────


def _get_scraper_state(context: ContextTypes.DEFAULT_TYPE) -> bool:
    if "scraper_enabled" not in context.bot_data:
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


def _is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.IPv4Address(ip.strip())
        return True
    except Exception:
        return False


def _build_source_list_buttons(sources: list) -> InlineKeyboardMarkup:
    buttons = []
    for src in sources:
        icon = "\U0001f4e1" if src.source_type == "telegram" else "\U0001f517"
        status_icon = "\U0001f7e2" if src.is_active else "\U0001f534"
        buttons.append([InlineKeyboardButton(
            f"{icon} {src.name} {status_icon}",
            callback_data=f"scraper_toggle_source:{src.id}",
        )])
    buttons.append([InlineKeyboardButton("\U0001f519 بازگشت", callback_data="scraper_menu")])
    return InlineKeyboardMarkup(buttons)


# ─── Health Command ─────────────────────────────────────────


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    factory = get_session_factory()
    try:
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return
            from utils.health import check_database_health, get_system_stats
            db_ok = await check_database_health(session)
            stats = await get_system_stats(session)
            users = await crud.count_users(session)
            starts = await crud.total_starts(session)
        scraper = "\U0001f7e2 فعال" if scraper_is_enabled(context) else "\U0001f534 غیرفعال"
        db_status = "\U0001f7e2 سالم" if db_ok else "\U0001f534 ناسالم"
        await update.message.reply_text(
            f"\U0001f48a سلامت سیستم\n\n"
            f"دیتابیس: {db_status}\n"
            f"\U0001f465 کاربران: {users}\n"
            f"\U0001f680 استارت‌ها: {starts}\n"
            f"\U0001f4e6 کانفیگ‌ها: {stats.get('configs', 'N/A')}\n"
            f"\U0001f4e1 اسکرپر: {scraper}"
        )
    except Exception as exc:
        logger.error("Health check failed: {}", exc)
        await update.message.reply_text("\u274c خطا در بررسی سلامت سیستم")


# ─── Admin Callback ─────────────────────────────────────────


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    factory = get_session_factory()

    admin_routes = {
        "admin_panel", "add_admin", "admin_users", "admin_stats",
        "admin_broadcast", "vip_panel", "vip_add", "vip_remove",
        "vip_list", "vip_broadcast", "clean_ip_menu", "clean_ip_upload",
        "list_clean_ip", "scraper_status", "scraper_toggle",
        "scraper_menu", "scraper_add_tg", "scraper_add_sub",
        "scraper_remove", "scraper_list",
        "ip_management_menu", "ip_single", "ip_bulk", "ip_file",
        "list_admins", "remove_admin", "health_check",
        "ip_config_count", "ip_generated_configs",
        "white_configs_menu",
        "request_white_configs_perf",
    }

    if data not in admin_routes and not data.startswith("scraper_toggle_source"):
        return False


    async with factory() as session:
        if not await require_admin(session, user_id):
            await query.answer("\u26d4 دسترسی ندارید", show_alert=True)
            return True

    if data == "admin_panel":
        await query.edit_message_text("\U0001f6e0 پنل مدیریت", reply_markup=admin_panel_menu())
        return True

    if data == "add_admin":
        if not await is_owner(user_id):
            await query.answer("\u26d4 فقط مالک", show_alert=True)
            return True
        context.user_data["awaiting_admin_id"] = True
        await query.edit_message_text(
            "\U0001f464 آیدی عددی ادمین جدید را ارسال کنید:",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "list_admins":
        async with factory() as session:
            admins = await crud.list_admins_with_info(session)
        if not admins:
            await query.edit_message_text("\u274c ادمینی ثبت نشده.", reply_markup=back_button("admin_panel"))
            return True
        text = "\U0001f4cb لیست ادمین‌ها\n\n"
        for i, adm in enumerate(admins, 1):
            text += f"{i}. `{adm.user_id}` — {adm.added_at:%Y-%m-%d}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button("admin_panel"))
        return True

    if data == "remove_admin":
        context.user_data["awaiting_remove_admin"] = True
        await query.edit_message_text(
            "\u274c آیدی عددی ادمین برای حذف:",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "admin_users":
        async with factory() as session:
            count = await crud.count_users(session)
        await query.edit_message_text(
            f"\U0001f465 تعداد کاربران: {count}",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "admin_stats":
        async with factory() as session:
            users = await crud.count_users(session)
            starts = await crud.total_starts(session)
        await query.edit_message_text(
            f"\U0001f4ca آمار\n\n\U0001f465 کاربران: {users}\n\U0001f680 استارت‌ها: {starts}",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "admin_broadcast":
        context.user_data["broadcast_mode"] = True
        await query.edit_message_text(
            "\U0001f4e2 پیام همگانی را ارسال کنید:",
            reply_markup=back_button("admin_panel"),
        )
        return True

    if data == "health_check":
        from utils.health import check_database_health, get_system_stats
        async with factory() as session:
            db_ok = await check_database_health(session)
            stats = await get_system_stats(session)
        scraper = "\U0001f7e2 فعال" if scraper_is_enabled(context) else "\U0001f534 غیرفعال"
        status_emoji = "\U0001f7e2" if db_ok else "\U0001f534"
        await query.edit_message_text(
            f"\U0001f48a سلامت سیستم\n\n"
            f"دیتابیس: {status_emoji} {'سالم' if db_ok else 'ناسالم'}\n"
            f"\U0001f465 کاربران: {stats.get('users', 'N/A')}\n"
            f"\U0001f4e6 کانفیگ‌ها: {stats.get('configs', 'N/A')}\n"
            f"\U0001f4e1 اسکرپر: {scraper}",
            reply_markup=back_button("admin_panel"),
        )
        return True

    # ─── White configs (performance) ───
    if data == "white_configs_menu":
        from app.bot.menus_refactor import white_configs_menu
        await query.edit_message_text(
            "📡 کانفیگ‌های سفید",
            reply_markup=white_configs_menu(),
        )
        return True

    if data == "request_white_configs_perf":
        context.user_data["awaiting_white_perf_count"] = True
        await query.edit_message_text(
            "📡 درخواست تست عملکرد (Alive/TTFB/Stability/Scoring)\n\n"
            "تعداد کانفیگ‌های مورد تست را وارد کنید (100 تا 1000):",
            reply_markup=back_button("white_configs_menu"),
        )
        return True

    if data == "ping_irancell":
        context.user_data["ping_operator"] = "irancell"
        context.user_data["awaiting_ping_threshold"] = True
        await query.edit_message_text(
            "📡 پینگ با ایرانسل\n\n"
            "عدد آستانه پینگ را وارد کنید (میلی‌ثانیه / ms).\n"
            "مثال: 120",
            reply_markup=back_button("white_configs_menu"),
        )
        return True

    if data == "ping_mci":
        context.user_data["ping_operator"] = "mci"
        context.user_data["awaiting_ping_threshold"] = True
        await query.edit_message_text(
            "📡 پینگ با همراه اول\n\n"
            "عدد آستانه پینگ را وارد کنید (میلی‌ثانیه / ms).\n"
            "مثال: 120",
            reply_markup=back_button("white_configs_menu"),
        )
        return True

    # ─── VIP ───
    if data == "vip_panel":
        await query.edit_message_text("\u2b50 پنل VIP", reply_markup=vip_panel_menu())
        return True

    if data == "vip_add":
        context.user_data["awaiting_vip_id"] = True
        await query.edit_message_text(
            "\U0001f464 آیدی VIP را ارسال کنید:",
            reply_markup=back_button("vip_panel"),
        )
        return True

    if data == "vip_remove":
        context.user_data["awaiting_vip_remove"] = True
        await query.edit_message_text(
            "\u274c آیدی VIP برای حذف:",
            reply_markup=back_button("vip_panel"),
        )
        return True

    if data == "vip_list":
        async with factory() as session:
            vips = await crud.list_vips(session)
        if not vips:
            await query.edit_message_text("\u274c VIP ثبت نشده.", reply_markup=back_button("vip_panel"))
            return True
        text = "\u2b50 لیست VIP\n\n"
        for i, vip in enumerate(vips[:50], 1):
            text += f"{i}. `{vip.user_id}` — {vip.added_at:%Y-%m-%d}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=back_button("vip_panel"))
        return True

    if data == "vip_broadcast":
        context.user_data["vip_broadcast_mode"] = True
        await query.edit_message_text(
            "\U0001f4e2 پیام VIP را ارسال کنید:",
            reply_markup=back_button("vip_panel"),
        )
        return True

    # ─── Clean IP ───
    if data == "clean_ip_menu":
        await query.edit_message_text("\U0001f310 مدیریت Clean IP", reply_markup=clean_ip_menu())
        return True

    if data == "clean_ip_upload":
        context.user_data["awaiting_clean_ip"] = True
        await query.edit_message_text(
            "\U0001f4c4 فایل txt آی‌پی‌ها را ارسال کنید:",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    if data == "list_clean_ip":
        async with factory() as session:
            count = await crud.count_clean_ips(session)
        await query.edit_message_text(
            f"\U0001f310 تعداد Clean IP: {count}",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    if data == "ip_config_count":
        context.user_data["awaiting_config_count"] = True
        await query.edit_message_text(
            "\U0001f4dc تعداد کانفیگ‌های مورد نظر برای هر IP را وارد کنید (مثلاً 5):",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    if data == "ip_generated_configs":
        async with factory() as session:
            # دریافت کانفیگ‌های ساخته شده با IPهای جدید در 24 ساعت گذشته
            cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_configs = await session.execute(
                select(ProcessedConfig)
                .where(and_(
                    ProcessedConfig.created_at >= cutoff,
                    ProcessedConfig.host.isnot(None)
                ))
                .order_by(desc(ProcessedConfig.created_at))
                .limit(50)
            )
            configs = recent_configs.scalars().all()

        if not configs:
            await query.edit_message_text(
                "\U0001f4c5 کانفیگ جدیدی با IPهای ساخته نشده است.",
                reply_markup=back_button("clean_ip_menu"),
            )
            return True

        text = "\U0001f4ca کانفیگ‌های ساخته شده با IPهای جدید (24 ساعت گذشته):\n\n"
        for i, config in enumerate(configs, 1):
            text += (
                f"{i}. **کشور:** `{config.country_code or 'نامشخص'}` "
                f"**پروتکل:** `{config.protocol or 'نامشخص'}` "
                f"**هاست:** `{config.host or 'نامشخص'}`\n"
            )

        await query.edit_message_text(
            text, 
            parse_mode="Markdown", 
            reply_markup=back_button("clean_ip_menu")
        )
        return True

    if data == "ip_single":
        context.user_data["awaiting_ip_single"] = True
        await query.edit_message_text(
            "\U0001f310 آی‌پی تکی را ارسال کنید:",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    if data == "ip_bulk":
        context.user_data["awaiting_ip_bulk"] = True
        await query.edit_message_text(
            "\U0001f4dd لیست آی‌پی‌ها را ارسال کنید (هر خط یک IP):",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    if data == "ip_file":
        context.user_data["awaiting_clean_ip"] = True
        await query.edit_message_text(
            "\U0001f4e4 فایل txt آی‌پی‌ها را ارسال کنید:",
            reply_markup=back_button("clean_ip_menu"),
        )
        return True

    # ─── Scraper control ───
    if data == "scraper_status":
        status = "\U0001f7e2 فعال" if scraper_is_enabled(context) else "\U0001f534 غیرفعال"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f504 تغییر وضعیت", callback_data="scraper_toggle")],
            [InlineKeyboardButton("\U0001f519 بازگشت", callback_data="admin_panel")],
        ])
        await query.edit_message_text(f"Scraper: {status}", reply_markup=kb)
        return True

    if data == "scraper_toggle":
        set_scraper_enabled(context, not scraper_is_enabled(context))
        status = "\U0001f7e2 فعال" if scraper_is_enabled(context) else "\U0001f534 غیرفعال"
        await query.answer(f"Scraper {status}", show_alert=True)
        return True

    # ─── Scraper management ───
    if data == "scraper_menu":
        enabled = scraper_is_enabled(context)
        status_text = "\U0001f7e2 فعال" if enabled else "\U0001f534 غیرفعال"
        await query.edit_message_text(
            f"\U0001f4e1 مدیریت اسکرپر\n\nوضعیت: {status_text}",
            reply_markup=scraper_management_menu(enabled),
        )
        return True

    if data == "scraper_add_tg":
        context.user_data["awaiting_scraper_tg"] = True
        await query.edit_message_text(
            "\U0001f4e1 نام کانال تلگرام را ارسال کنید (با @ یا بدون آن):",
            reply_markup=back_button("scraper_menu"),
        )
        return True

    if data == "scraper_add_sub":
        context.user_data["awaiting_scraper_sub"] = True
        await query.edit_message_text(
            "\U0001f517 لینک اشتراک (Subscription URL) را ارسال کنید:",
            reply_markup=back_button("scraper_menu"),
        )
        return True

    if data == "scraper_remove":
        async with factory() as session:
            sources = await crud.list_scraper_sources(session)
        if not sources:
            await query.edit_message_text(
                "\u274c هیچ منبعی ثبت نشده است.",
                reply_markup=back_button("scraper_menu"),
            )
            return True
        await query.edit_message_text(
            "\U0001f5d1 منبعی را برای تغییر وضعیت انتخاب کنید:",
            reply_markup=_build_source_list_buttons(sources),
        )
        return True

    if data.startswith("scraper_toggle_source"):
        source_id = int(data.split(":")[1])
        async with factory() as session:
            source = await crud.toggle_scraper_source(session, source_id)
        if source:
            status_text = "فعال" if source.is_active else "غیرفعال"
            type_text = "کانال تلگرام" if source.source_type == "telegram" else "لینک اشتراک"
            await query.answer(f"\u2705 **{source.name}** ({type_text}) با موفقیت {status_text} شد!", show_alert=True)
        else:
            await query.answer("\u274c منبع یافت نشد", show_alert=True)
        async with factory() as session:
            sources = await crud.list_scraper_sources(session)
        await query.edit_message_text(
            "\U0001f5d1 منبعی را برای تغییر وضعیت انتخاب کنید:",
            reply_markup=_build_source_list_buttons(sources),
        )
        return True

    if data == "scraper_list":
        async with factory() as session:
            sources = await crud.list_scraper_sources(session)
        if not sources:
            await query.edit_message_text(
                "\u274c هیچ منبعی ثبت نشده است.",
                reply_markup=back_button("scraper_menu"),
            )
            return True
        text = "\U0001f4cb لیست منابع اسکرپر:\n\n"
        for i, src in enumerate(sources, 1):
            icon = "\U0001f4e1" if src.source_type == "telegram" else "\U0001f517"
            status_icon = "\U0001f7e2" if src.is_active else "\U0001f534"
            status_text = "فعال" if src.is_active else "غیرفعال"
            type_text = "کانال تلگرام" if src.source_type == "telegram" else "لینک اشتراک"
            # پاک‌سازی نام منبع از کاراکترهای مشکل‌ساز
            safe_name = src.name.replace("*", "").replace("_", "").replace("`", "")
            text += f"{i}. {icon} {safe_name}\n   - نوع: {type_text}\n   - وضعیت: {status_text}\n   - لینک: {src.url}\n\n"
        await query.edit_message_text(text, parse_mode=None, reply_markup=back_button("scraper_menu"))
        return True

    return False


# ─── Admin Text Handler ─────────────────────────────────────


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    factory = get_session_factory()

    # ─── Add admin ───
    if context.user_data.get("awaiting_admin_id"):
        context.user_data.pop("awaiting_admin_id", None)
        if not await is_owner(user_id):
            await update.message.reply_text("\u26d4 فقط مالک", reply_markup=admin_panel_menu())
            return True
        try:
            new_id = int(text)
        except ValueError:
            await update.message.reply_text("\u274c آیدی نامعتبر", reply_markup=vip_panel_menu())
            return True
        async with factory() as session:
            added = await crud.add_admin(session, new_id, user_id)
        msg = "\u2705 ادمین اضافه شد" if added else "\u26a0\ufe0f از قبل ادمین بود"
        await update.message.reply_text(msg, reply_markup=admin_panel_menu())
        return True

    # ─── Remove admin ───
    if context.user_data.get("awaiting_remove_admin"):
        context.user_data.pop("awaiting_remove_admin", None)
        if not await is_owner(user_id):
            await update.message.reply_text("\u26d4 فقط مالک", reply_markup=admin_panel_menu())
            return True
        try:
            remove_id = int(text)
        except ValueError:
            await update.message.reply_text("\u274c آیدی نامعتبر", reply_markup=vip_panel_menu())
            return True
        async with factory() as session:
            removed = await crud.remove_admin(session, remove_id)
        msg = "\u2705 ادمین حذف شد" if removed else "\u26a0\ufe0f ادمین یافت نشد"
        await update.message.reply_text(msg, reply_markup=admin_panel_menu())
        return True

    # ─── VIP add ───
    if context.user_data.get("awaiting_vip_id"):
        context.user_data.pop("awaiting_vip_id", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return True
        try:
            vip_id = int(text)
        except ValueError:
            await update.message.reply_text("\u274c آیدی نامعتبر", reply_markup=vip_panel_menu())
            return True
        async with factory() as session:
            await crud.add_vip(session, vip_id)
        await update.message.reply_text(f"\u2705 VIP {vip_id} اضافه شد", reply_markup=vip_panel_menu())
        return True

    # ─── VIP remove ───
    if context.user_data.get("awaiting_vip_remove"):
        context.user_data.pop("awaiting_vip_remove", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                return True
        try:
            vip_id = int(text)
        except ValueError:
            await update.message.reply_text("\u274c آیدی نامعتبر", reply_markup=vip_panel_menu())
            return True
        async with factory() as session:
            await crud.remove_vip(session, vip_id)
        await update.message.reply_text(f"\u2705 VIP {vip_id} حذف شد", reply_markup=vip_panel_menu())
        return True

    # ─── IP single ───
    if context.user_data.get("awaiting_ip_single"):
        context.user_data.pop("awaiting_ip_single", None)
        ip = text.strip()
        if not _is_valid_ip(ip):
            await update.message.reply_text("\u274c آی‌پی نامعتبر", reply_markup=clean_ip_menu())
            return True
        async with factory() as session:
            await crud.add_clean_ip(session, ip)
        await update.message.reply_text(f"\u2705 IP {ip} ذخیره شد", reply_markup=clean_ip_menu())
        return True

    # ─── IP bulk ───
    if context.user_data.get("awaiting_ip_bulk"):
        context.user_data.pop("awaiting_ip_bulk", None)
        count = 0
        invalid = 0
        for candidate in text.strip().split():
            candidate = candidate.strip()
            if _is_valid_ip(candidate):
                async with factory() as session:
                    await crud.add_clean_ip(session, candidate)
                count += 1
            else:
                invalid += 1
        msg = f"\u2705 {count} IP ذخیره شد"
        if invalid > 0:
            msg += f"\n\u26a0\ufe0f {invalid} IP نامعتبر"
        await update.message.reply_text(msg, reply_markup=clean_ip_menu())
        return True

    # ─── Scraper: add telegram source ───
    if context.user_data.get("awaiting_scraper_tg"):
        context.user_data.pop("awaiting_scraper_tg", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return True
        channel = text.lstrip("@")
        if not channel:
            await update.message.reply_text("\u274c نام کانال نامعتبر است", reply_markup=scraper_menu())
            return True
        async with factory() as session:
            result = await crud.add_scraper_source(
                session, name=channel, url=channel, source_type="telegram"
            )
        if result == "added":
            await update.message.reply_text(f"\u2705 کانال با موفقیت اضافه شد\n\nنام: @{channel}\nنوع: کانال تلگرام", reply_markup=scraper_menu())
        elif result == "duplicate_url":
            await update.message.reply_text(f"\u26a0\ufe0f این کانال قبلاً اضافه شده است\n\nنام: @{channel}", reply_markup=scraper_menu())
        else:
            await update.message.reply_text(f"\u26a0\ufe0f این نام قبلاً استفاده شده است\n\nنام: @{channel}", reply_markup=scraper_menu())
        return True

    # ─── Scraper: add subscription source ───
    if context.user_data.get("awaiting_scraper_sub"):
        context.user_data.pop("awaiting_scraper_sub", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return True
        url = text.strip()
        if not url.startswith(("http://", "https://", "sub://")):
            await update.message.reply_text("\u274c لینک نامعتبر است", reply_markup=scraper_menu())
            return True
        name = url.split("/")[-1][:80] if "/" in url else url[:80]
        async with factory() as session:
            result = await crud.add_scraper_source(
                session, name=name, url=url, source_type="subscription"
            )
        if result == "added":
            await update.message.reply_text("\u2705 لینک اشتراک با موفقیت اضافه شد\n\nنام: {}\nلینک: {}".format(name, url), reply_markup=scraper_menu())
        elif result == "duplicate_url":
            await update.message.reply_text("\u26a0\ufe0f این لینک قبلاً اضافه شده است\n\nلینک: {}".format(url), reply_markup=scraper_menu())
        else:
            await update.message.reply_text("\u26a0\ufe0f این نام قبلاً استفاده شده است\n\nنام: {}".format(name), reply_markup=scraper_menu())
        return True

    # ─── Broadcast ───
    if context.user_data.get("broadcast_mode"):
        context.user_data.pop("broadcast_mode", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return True
            user_ids = await crud.get_all_user_ids(session)

        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent += 1
                await asyncio.sleep(BROADCAST_DELAY_SECONDS)
            except Exception as exc:
                logger.error("Broadcast failed for user {}: {}", uid, exc)
                failed += 1

        msg = f"\u2705 ارسال به {sent} کاربر"
        if failed > 0:
            msg += f"\n\u26a0\ufe0f {failed} کاربر ارسال نشد"
        await update.message.reply_text(msg, reply_markup=admin_panel_menu())
        return True

    # ─── VIP broadcast ───
    if context.user_data.get("vip_broadcast_mode"):
        context.user_data.pop("vip_broadcast_mode", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return True
            vip_ids = await crud.get_vip_ids(session)

        sent = 0
        failed = 0
        for uid in vip_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                sent += 1
                await asyncio.sleep(BROADCAST_DELAY_SECONDS)
            except Exception as exc:
                logger.error("VIP broadcast failed for user {}: {}", uid, exc)
                failed += 1

        msg = f"\u2705 ارسال به {sent} VIP"
        if failed > 0:
            msg += f"\n\u26a0\ufe0f {failed} VIP ارسال نشد"
        await update.message.reply_text(msg, reply_markup=vip_panel_menu())
        return True

    # ─── White configs performance count ───
    if context.user_data.get("awaiting_white_perf_count"):

        context.user_data.pop("awaiting_white_perf_count", None)

        # request count (100..1000) -> top_n
        try:
            cfg_count = int(text)
        except Exception:
            cfg_count = 0

        if cfg_count < 100 or cfg_count > 1000:
            await update.message.reply_text(
                "❌ تعداد نامعتبر است. باید بین 100 تا 1000 باشد.",
                reply_markup=admin_panel_menu(),
            )
            return True

        from core.config import BASE_DIR
        from core.white_configs_perf_tester import (
            evaluate_white_configs,
            export_perf_results_to_txt,
        )

        # xray binary must exist inside project root ./bin
        # Expected:
        #   {BASE_DIR}/bin/xray
        #   {BASE_DIR}/bin/xray.exe
        xray_bin = BASE_DIR / "bin" / "xray"
        if not xray_bin.exists():
            xray_bin = BASE_DIR / "bin" / "xray.exe"

        if not xray_bin.exists():
            expected_dir = (BASE_DIR / "bin").as_posix()
            await update.message.reply_text(
                "❌ فایل xray پیدا نشد.\n\n"
                "فایل باید دقیقاً داخل مسیر زیر باشد:\n"
                f"📁 {expected_dir}\n\n"
                "نام‌های قابل قبول:\n"
                "• xray\n"
                "• xray.exe\n\n"
                "بعد از قرار دادن فایل، دوباره از منو "
                "گزینه '📡 درخواست تست عملکرد' را اجرا کن.",
                reply_markup=white_configs_menu(),
            )
            return True

        # operator name (no threshold in this perf tester)
        operator_title = context.user_data.get("ping_operator", "unknown")
        if operator_title == "unknown":
            operator_title = "white-perf"

        # select candidates
        async with factory() as session:
            rows = (
                await session.execute(
                    select(ProcessedConfig)
                    .where(ProcessedConfig.is_valid == True)
                    .order_by(desc(ProcessedConfig.created_at))
                    .limit(500)
                )
            ).scalars().all()

        if not rows:
            await update.message.reply_text(
                "❌ کانفیگ معتبر برای تست یافت نشد.",
                reply_markup=admin_panel_menu(),
            )
            return True

        temp_root = BASE_DIR / "data" / "temp" / "white_perf"
        export_dir = BASE_DIR / "data" / "exports" / "white_perf"
        export_dir.mkdir(parents=True, exist_ok=True)

        out_path = export_dir / f"white_perf_{operator_title}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"

        await update.message.reply_text(
            f"⏳ در حال تست White configs برای {len(rows)} کانفیگ...\n"
            f"Top results: {cfg_count}",
            reply_markup=admin_panel_menu(),
        )

        results = await evaluate_white_configs(
            rows=rows,
            top_n=cfg_count,
            xray_bin_path=xray_bin,
            temp_root=temp_root,
        )

        txt = export_perf_results_to_txt(operator=operator_title, results=results)
        out_path.write_text(txt, encoding="utf-8")

        with open(out_path, "rb") as doc:
            await update.message.reply_document(
                document=doc,
                filename=out_path.name,
                caption=f"📦 خروجی White perf ({operator_title})\nResults: {len(results)}",
            )

        await update.message.reply_text(
            "✅ عملیات تکمیل شد.",
            reply_markup=admin_panel_menu(),
        )
        return True

    # ─── Config count ───
    if context.user_data.get("awaiting_config_count"):

        context.user_data.pop("awaiting_config_count", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return True

        try:
            config_count = int(text)
            if config_count <= 0 or config_count > 20:
                await update.message.reply_text(
                    "\u274c تعداد باید بین 1 تا 20 باشد", 
                    reply_markup=clean_ip_menu()
                )
                return True

            # ذخیره تعداد در context.user_data برای استفاده بعدی
            context.user_data["config_count_per_ip"] = config_count
            context.user_data["awaiting_ip_count"] = True
            await update.message.reply_text(
                f"\u2705 تعداد کانفیگ‌ها روی {config_count} تنظیم شد.\n"
                f"\U0001f4cc حالا تعداد IPها را وارد کنید (حداکثر 50):",
                reply_markup=clean_ip_menu()
            )
            return True

        except ValueError:
            await update.message.reply_text(
                "\u274c تعداد نامعتبر است", 
                reply_markup=clean_ip_menu()
            )
            return True

    # ─── IP count ───
    if context.user_data.get("awaiting_ip_count"):
        context.user_data.pop("awaiting_ip_count", None)
        async with factory() as session:
            if not await require_admin(session, user_id):
                await update.message.reply_text("\u26d4 دسترسی ندارید")
                return True

        try:
            ip_count = int(text)
            if ip_count <= 0 or ip_count > 50:
                await update.message.reply_text(
                    "\u274c تعداد باید بین 1 تا 50 باشد",
                    reply_markup=clean_ip_menu()
                )
                return True

            config_count = context.user_data.get("config_count_per_ip", 1)
            if config_count <= 0:
                config_count = 1

            from core.config import BASE_DIR
            from core.ip_manager import apply_ips_to_configs
            from core.utils import detect_protocol

            # مسیر خروجی txt
            export_dir = BASE_DIR / "data" / "exports"
            export_dir.mkdir(parents=True, exist_ok=True)

            cutoff = datetime.utcnow() - timedelta(hours=24)

            async with factory() as session:
                # 1) IPهای تمیز «ارائه‌شده» توسط ادمین:
                # در نبود batch-id، ورودی عملی ادمین همان رکوردهای CleanIP است.
                clean_ips_query = await session.execute(
                    select(CleanIP.ip)
                    .order_by(desc(CleanIP.created_at))
                    .limit(ip_count)
                )
                clean_ips = [row[0] for row in clean_ips_query.all()]

                if not clean_ips:
                    await update.message.reply_text(
                        "\u274c هیچ IP تمیزی در دیتابیس یافت نشد.",
                        reply_markup=clean_ip_menu()
                    )
                    return True

                # 2) کانفیگ‌های پایه اسکن‌شده معتبر:
                # - trojan استثنا است (اسکن/تبدیل هم نداشته باش)
                # - کانفیگ‌هایی که host آنها همان IPهای تمیز ادمین است، در بازتولید استفاده نشوند
                base_configs_query = await session.execute(
                    select(ProcessedConfig)
                    .where(
                        and_(
                            ProcessedConfig.created_at >= cutoff,
                            ProcessedConfig.is_valid == True,
                            ProcessedConfig.raw_config.isnot(None),
                            ProcessedConfig.protocol != "trojan",
                            ProcessedConfig.host.not_in(clean_ips),
                        )
                    )
                    .order_by(desc(ProcessedConfig.created_at))
                    .limit(config_count)
                )
                base_configs = base_configs_query.scalars().all()

                if not base_configs:
                    await update.message.reply_text(
                        "\u274c کانفیگ اسکن‌شده معتبر (غیر trojan) برای اعمال IP پیدا نشد.",
                        reply_markup=clean_ip_menu()
                    )
                    return True

            # 3) اعمال IPها روی کانفیگ‌های پایه و تولید خروجی
            #    apply_per_ip=config_count و configs=len(config_count) => خروجی ip_count*config_count
            #    configs باید لیست ردیف‌های ProcessedConfig باشد.
            output_configs = await apply_ips_to_configs(
                ips=clean_ips,
                configs=base_configs,
                apply_per_ip=config_count
            )

            # 4) ساخت فایل txt
            # output_configs ممکن است شامل None نباشد؛ ولی برای امنیت فیلتر می‌کنیم.
            output_texts = [c for c in output_configs if c]
            if not output_texts:
                await update.message.reply_text(
                    "\u274c خطا در تولید خروجی کانفیگ‌ها.",
                    reply_markup=clean_ip_menu()
                )
                return True

            # فیلتر trojan هنگام خروجی (طبق درخواست شما)
            # نکته: خروجی باید دقیقاً لینک خام باشد تا در V2Ray/V2N خودکار کپی/Import شود.
            filtered_texts: list[str] = []
            for item in output_texts:
                # حالت اصلی: item خودش string لینک است
                if isinstance(item, str):
                    cfg = item.strip()
                    if not cfg:
                        continue
                    if detect_protocol(cfg) == "trojan":
                        continue
                    filtered_texts.append(cfg)
                    continue

                # حالت fallback: اگر item dict باشد یا چیز دیگری، تلاش می‌کنیم لینک را استخراج کنیم
                cfg = None
                if isinstance(item, dict):
                    # فیلدهای محتمل
                    for key in ("watermarked_config", "config", "link", "url"):
                        if key in item and isinstance(item[key], str):
                            candidate = item[key].strip()
                            if candidate:
                                cfg = candidate
                                break

                if not cfg:
                    # اگر نتوانستیم چیزی استخراج کنیم، این رکورد را رد می‌کنیم
                    continue

                if detect_protocol(cfg) == "trojan":
                    continue
                filtered_texts.append(cfg)

            if not filtered_texts:
                await update.message.reply_text(
                    "\u274c خروجی تولید شد، اما همه کانفیگ‌ها trojan بودند و حذف شدند.",
                    reply_markup=clean_ip_menu()
                )
                return True

            # جداکننده‌های دو خط خالی مثل خروجی کاربر
            txt = "\n\n".join(filtered_texts)

            filename = f"clean_configs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_ips{len(clean_ips)}_cfg{config_count}.txt"
            out_path = export_dir / filename
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(txt)

            await update.message.reply_text(
                f"\u2705 خروجی با موفقیت آماده شد: {len(filtered_texts)} کانفیگ جدید",
                reply_markup=clean_ip_menu()
            )

            with open(out_path, "rb") as doc:
                await update.message.reply_document(
                    document=doc,
                    filename=filename,
                    caption="📦 کانفیگ‌های جدید (Clean IP اعمال شد)",
                    parse_mode=None
                )
            return True

        except ValueError:
            await update.message.reply_text(
                "\u274c تعداد نامعتبر است",
                reply_markup=clean_ip_menu()
            )
            return True

    return False


# ─── Document Handler ───────────────────────────────────────


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_clean_ip"):
        return

    user_id = update.effective_user.id
    factory = get_session_factory()
    async with factory() as session:
        if not await require_admin(session, user_id):
            await update.message.reply_text("\u26d4 دسترسی ندارید")
            return

    document = update.message.document
    if not document or not document.file_name.endswith(".txt"):
        await update.message.reply_text("\u274c فقط فایل .txt")
        return

    file = await document.get_file()
    from core.config import BASE_DIR
    dest_dir = BASE_DIR / "data" / "clean_ips"
    dest_dir.mkdir(parents=True, exist_ok=True)

    import re as _re
    original_name = document.file_name
    safe_name = _re.sub(r"[\/]+", "_", original_name)
    safe_name = safe_name.replace("..", "")
    safe_name = _re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
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
            await update.message.reply_text(f"\u274c خطا در خواندن فایل: {exc}")
            context.user_data.pop("awaiting_clean_ip", None)
            return

    context.user_data.pop("awaiting_clean_ip", None)
    msg = f"\u2705 {count} IP ذخیره شد"
    if invalid > 0:
        msg += f"\n\u26a0\ufe0f {invalid} IP نامعتبر نادیده گرفته شد"
    await update.message.reply_text(msg, reply_markup=clean_ip_menu())
