# app/handlers/user.py — handlerهای کاربر (منو، export، فیلتر)

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.menus import country_menu, main_menu, protocol_menu
from app.middlewares.auth import is_admin
from constants import EXPORT_DEFAULT_LAST, EXPORT_MAX_COUNT, EXPORT_MIN_COUNT
from core.config import BASE_DIR
from core.logger import get_logger
from database.crud import filter_configs, get_last_configs
from database.session import get_session_factory

logger = get_logger()
EXPORT_DIR = BASE_DIR / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


async def _admin_flag(user_id: int) -> bool:
    factory = get_session_factory()
    async with factory() as session:
        return await is_admin(session, user_id)


def _build_export_file(configs: list, filename: str) -> Path:
    """ساخت فایل txt از کانفیگ‌های watermarked."""
    path = EXPORT_DIR / f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(path, "w", encoding="utf-8") as f:
            for row in configs:
                text = row.watermarked_config or row.raw_config
                f.write(text + "\n\n")
        return path
    except Exception as exc:
        logger.error("Error building export file {}: {}", filename, exc)
        raise


def _build_export_text(configs: list) -> str:
    """ساخت متن از کانفیگ‌های watermarked."""
    lines = []
    for row in configs:
        text = row.watermarked_config or row.raw_config
        lines.append(text)
    return "\n\n".join(lines)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /start — ثبت کاربر و نمایش منو."""
    user = update.effective_user
    factory = get_session_factory()
    try:
        async with factory() as session:
            from database import crud

            await crud.upsert_user(session, user.id, user.first_name, user.username)
            await crud.bump_user_start(session, user.id)
            admin = await is_admin(session, user.id)

        await update.message.reply_text(
            "👋 به ربات Config Manager خوش آمدید!\nاز منوی زیر استفاده کنید:",
            reply_markup=main_menu(admin),
        )
    except Exception as exc:
        logger.error("Error in start command for user {}: {}", user.id, exc)
        await update.message.reply_text("❌ خطا در ثبت‌نام. لطفا بعدا تلاش کنید.")


async def user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    callbackهای کاربر.
    Returns True اگر handle شد، False برای واگذاری به admin.
    """
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # ─── Navigation ───
    if data == "back_main":
        context.user_data.clear()
        await query.edit_message_text(
            "🏠 منوی اصلی",
            reply_markup=main_menu(await _admin_flag(user_id)),
        )
        return True

    if data == "menu_country":
        await query.edit_message_text("🌍 کشور را انتخاب کنید:", reply_markup=country_menu())
        return True

    if data == "menu_protocol":
        context.user_data.pop("country", None)
        await query.edit_message_text("⚙️ پروتکل را انتخاب کنید:", reply_markup=protocol_menu())
        return True

    if data == "menu_custom":
        context.user_data["awaiting_count"] = True
        await query.edit_message_text("🔢 تعداد مورد نظر را ارسال کنید (۱ تا ۱۰۰۰۰):")
        return True

    # ─── Export last N ───
    if data == "last_20":
        try:
            await query.edit_message_text("📦 در حال آماده‌سازی...")
            factory = get_session_factory()
            async with factory() as session:
                rows = await get_last_configs(session, EXPORT_DEFAULT_LAST * 2)
            if not rows:
                await query.message.reply_text("❌ کانفیگی یافت نشد.", reply_markup=main_menu(await _admin_flag(user_id)))
                return True

            # Build text from last 20
            text = _build_export_text(rows[:20])

            # Try to send as text message
            if len(text) < 3800:
                try:
                    await query.message.reply_text(
                        f"<pre>{text}</pre>",
                        parse_mode="HTML"
                    )
                    await query.message.reply_text("🏠 منوی اصلی", reply_markup=main_menu(await _admin_flag(user_id)))
                except Exception:
                    # Fallback to file if text too long
                    logger.warning("Text message too long, falling back to file")
                    path = _build_export_file(rows[:20], "last_20")
                    with open(path, "rb") as doc:
                        await query.message.reply_document(document=doc, caption="📦 آخرین ۲۰ کانفیگ")
                    await query.message.reply_text("🏠 منوی اصلی", reply_markup=main_menu(await _admin_flag(user_id)))
            else:
                # Send as file if too long
                path = _build_export_file(rows[:20], "last_20")
                with open(path, "rb") as doc:
                    await query.message.reply_document(document=doc, caption="📦 آخرین ۲۰ کانفیگ")
                await query.message.reply_text("🏠 منوی اصلی", reply_markup=main_menu(await _admin_flag(user_id)))
        except Exception as exc:
            logger.error("Error in last_20 export: {}", exc)
            await query.message.reply_text(f"❌ خطا: {exc}", reply_markup=main_menu(await _admin_flag(user_id)))
        return True

    # ─── Country select ───
    if data.startswith("country_"):
        country = data.replace("country_", "")
        context.user_data["country"] = country
        await query.edit_message_text(
            f"🌍 کشور: {country}\n⚙️ پروتکل را انتخاب کنید:",
            reply_markup=protocol_menu("menu_country"),
        )
        return True

    # ─── Protocol filter ───
    if data.startswith("proto_"):
        try:
            proto = data.replace("proto_", "")
            country = context.user_data.get("country")
            await query.edit_message_text(f"⏳ فیلتر...\n🌍 {country or 'همه'} | ⚙️ {proto}")

            factory = get_session_factory()
            async with factory() as session:
                rows = await filter_configs(
                    session,
                    country_code=country,
                    protocol=proto,
                    limit=1000,
                )

            if not rows:
                await query.message.reply_text(
                    "❌ کانفیگی یافت نشد.",
                    reply_markup=main_menu(await _admin_flag(user_id)),
                )
                return True

            path = _build_export_file(rows, f"{country or 'all'}_{proto}")
            with open(path, "rb") as doc:
                await query.message.reply_document(document=doc, caption=f"📦 تعداد: {len(rows)}")
            await query.message.reply_text("🏠 منوی اصلی", reply_markup=main_menu(await _admin_flag(user_id)))
        except Exception as exc:
            logger.error("Error in protocol filter: {}", exc)
            await query.message.reply_text(f"❌ خطا: {exc}", reply_markup=main_menu(await _admin_flag(user_id)))
        return True

    return False


async def handle_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """پردازش متن کاربر (custom count). Returns True if handled."""
    if not context.user_data.get("awaiting_count"):
        return False

    context.user_data.pop("awaiting_count", None)
    user_id = update.effective_user.id
    text = update.message.text.strip()

    try:
        count = int(text)
        if count < EXPORT_MIN_COUNT or count > EXPORT_MAX_COUNT:
            raise ValueError(f"تعداد باید بین {EXPORT_MIN_COUNT} و {EXPORT_MAX_COUNT} باشد")
    except ValueError as exc:
        logger.warning("Invalid count input from user {}: {}", user_id, exc)
        await update.message.reply_text(
            f"❌ عدد نامعتبر (بین {EXPORT_MIN_COUNT} و {EXPORT_MAX_COUNT})",
            reply_markup=main_menu(await _admin_flag(user_id)),
        )
        return True

    try:
        factory = get_session_factory()
        async with factory() as session:
            rows = await get_last_configs(session, count)

        if not rows:
            await update.message.reply_text("❌ کانفیگی یافت نشد.", reply_markup=main_menu(await _admin_flag(user_id)))
            return True

        path = _build_export_file(rows, f"custom_{count}")
        with open(path, "rb") as doc:
            await update.message.reply_document(document=doc, caption=f"📦 {len(rows)} کانفیگ")
        await update.message.reply_text("✅ انجام شد", reply_markup=main_menu(await _admin_flag(user_id)))
    except Exception as exc:
        logger.error("Error in custom count export for user {}: {}", user_id, exc)
        await update.message.reply_text(f"❌ خطا: {exc}", reply_markup=main_menu(await _admin_flag(user_id)))

    return True
