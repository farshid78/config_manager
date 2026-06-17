# app/handlers/user.py — handlerهای کاربر (منو، export، فیلتر)
# تمام پیام‌ها و لاگ‌ها به فارسی حرفه‌ای

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.menus_refactor import country_menu, main_menu, protocol_menu
from app.middlewares.auth import is_admin
from constants import COUNTRY_LABELS, EXPORT_DEFAULT_LAST, EXPORT_MAX_COUNT, EXPORT_MIN_COUNT
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
        logger.error("Error building output file {}: {}", filename, exc)
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
            "👋 <b>به ربات Config Manager خوش آمدید!</b>\n\n"
            "💡 از منوی زیر گزینه مورد نظر را انتخاب کنید:\n"
            "🌍 <b>کشورها</b> — دریافت کانفیگ بر اساس کشور\n"
            "⚙️ <b>پروتکل</b> — فیلتر بر اساس نوع پروتکل\n"
            "📦 <b>آخرین ۲۰</b> — دریافت ۲۰ کانفیگ اخیر\n"
            "🔢 <b>دلخواه</b> — دریافت تعداد دلخواه کانفیگ",
            parse_mode="HTML",
            reply_markup=main_menu(admin),
        )
        logger.info("User {} ({}) started the bot", user.id, user.first_name)
    except Exception as exc:
        logger.error("Error registering user {}: {}", user.id, exc)
        await update.message.reply_text(
            "❌ <b>خطا در ثبت‌نام!</b>\n\n"
            "⚠️ لطفاً بعداً تلاش کنید.",
            parse_mode="HTML",
        )


async def user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    callbackهای کاربر.
    Returns True اگر handle شد، False برای واگذاری به admin.
    """
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    # ─── بازگشت به منوی اصلی ───
    if data == "back_main":
        context.user_data.clear()
        await query.edit_message_text(
            "🏠 <b>منوی اصلی</b>\n\n"
            "💡 گزینه مورد نظر خود را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=main_menu(await _admin_flag(user_id)),
        )
        return True

    # ─── منوی کشورها ───
    if data == "menu_country":
        await query.edit_message_text(
            "🌍 <b>انتخاب کشور</b>\n\n"
            "💡 کشور مورد نظر خود را انتخاب کنید تا کانفیگ‌های آن کشور نمایش داده شود:",
            parse_mode="HTML",
            reply_markup=country_menu(),
        )
        return True

    # ─── منوی پروتکل ───
    if data == "menu_protocol":
        context.user_data.pop("country", None)
        await query.edit_message_text(
            "⚙️ <b>انتخاب پروتکل</b>\n\n"
            "💡 پروتکل مورد نظر خود را انتخاب کنید:\n"
            "• 🔵 VLESS — سریع و سبک\n"
            "• 🟡 VMESS — پایدار و محبوب\n"
            "• 🟣 TROJAN — امن و قابل‌اعتماد\n"
            "• ⚫ SHADOWSOCKS — ساده و کارآمد",
            parse_mode="HTML",
            reply_markup=protocol_menu(),
        )
        return True

    # ─── تعداد دلخواه ───
    if data == "menu_custom":
        context.user_data["awaiting_count"] = True
        await query.edit_message_text(
            "🔢 <b>دریافت کانفیگ دلخواه</b>\n\n"
            "📌 تعداد کانفیگ مورد نظر خود را ارسال کنید.\n"
            f"📝 محدوده: از <b>{EXPORT_MIN_COUNT}</b> تا <b>{EXPORT_MAX_COUNT}</b>",
            parse_mode="HTML",
        )
        return True

    # ─── آخرین ۲۰ کانفیگ ───
    if data == "last_20":
        try:
            await query.edit_message_text("📦 <b>در حال آماده‌سازی...</b>", parse_mode="HTML")
            factory = get_session_factory()
            async with factory() as session:
                rows = await get_last_configs(session, EXPORT_DEFAULT_LAST * 2)
            if not rows:
                await query.message.reply_text(
                    "❌ <b>کانفیگی یافت نشد!</b>\n\n"
                    "⚠️ هنوز کانفیگی در دیتابیس ثبت نشده است.\n"
                    "💡 لطفاً بعداً تلاش کنید.",
                    parse_mode="HTML",
                    reply_markup=main_menu(await _admin_flag(user_id)),
                )
                return True

            text = _build_export_text(rows[:20])

            if len(text) < 3800:
                try:
                    await query.message.reply_text(
                        f"📦 <b>آخرین ۲۰ کانفیگ</b>\n\n<pre>{text}</pre>",
                        parse_mode="HTML",
                    )
                except Exception:
                    logger.warning("Output text too long, sending as file")
                    path = _build_export_file(rows[:20], "last_20")
                    with open(path, "rb") as doc:
                        await query.message.reply_document(
                            document=doc,
                            caption="📦 آخرین ۲۰ کانفیگ",
                        )
            else:
                path = _build_export_file(rows[:20], "last_20")
                with open(path, "rb") as doc:
                    await query.message.reply_document(
                        document=doc,
                        caption="📦 آخرین ۲۰ کانفیگ",
                    )
            await query.message.reply_text(
                "🏠 <b>منوی اصلی</b>",
                parse_mode="HTML",
                reply_markup=main_menu(await _admin_flag(user_id)),
            )
        except Exception as exc:
            logger.error("Error sending last 20 configs: {}", exc)
            await query.message.reply_text(
                f"❌ <b>خطا در دریافت کانفیگ!</b>\n\n{exc}",
                parse_mode="HTML",
                reply_markup=main_menu(await _admin_flag(user_id)),
            )
        return True

    # ─── انتخاب کشور ───
    if data.startswith("country_"):
        country = data.replace("country_", "")
        context.user_data["country"] = country
        from core.utils import get_flag
        flag = get_flag(country)
        country_name = COUNTRY_LABELS.get(country, country) if COUNTRY_LABELS else country
        await query.edit_message_text(
            f"{flag} <b>کشور: {country_name}</b>\n\n"
            "⚙️ حالا پروتکل مورد نظر خود را انتخاب کنید:",
            parse_mode="HTML",
            reply_markup=protocol_menu("menu_country"),
        )
        return True

    # ─── فیلتر پروتکل ───
    if data.startswith("proto_"):
        try:
            proto = data.replace("proto_", "")
            country = context.user_data.get("country")
            from core.utils import get_flag
            flag = get_flag(country) if country else "🌍"
            country_display = country or "همه"
            await query.edit_message_text(
                f"⏳ <b>در حال فیلتر...</b>\n{flag} {country_display} | ⚙️ {proto}",
                parse_mode="HTML",
            )

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
                    "❌ <b>کانفیگی یافت نشد!</b>\n\n"
                    f"🔍 فیلتر: {flag} {country_display} | ⚙️ {proto}\n"
                    "💡 لطفاً فیلتر دیگری را امتحان کنید.",
                    parse_mode="HTML",
                    reply_markup=main_menu(await _admin_flag(user_id)),
                )
                return True

            text = _build_export_text(rows)
            if len(text) < 3800:
                try:
                    await query.message.reply_text(
                        f"{flag} <b>{country_display}</b> | ⚙️ {proto}\n"
                        f"📦 تعداد: <b>{len(rows)}</b>\n\n"
                        f"<pre>{text}</pre>",
                        parse_mode="HTML",
                    )
                except Exception:
                    path = _build_export_file(rows, f"{country or 'all'}_{proto}")
                    with open(path, "rb") as doc:
                        await query.message.reply_document(
                            document=doc,
                            caption=f"📦 {flag} {country_display} | {proto} | تعداد: {len(rows)}",
                        )
            else:
                path = _build_export_file(rows, f"{country or 'all'}_{proto}")
                with open(path, "rb") as doc:
                    await query.message.reply_document(
                        document=doc,
                        caption=f"📦 {flag} {country_display} | {proto} | تعداد: {len(rows)}",
                    )
            await query.message.reply_text(
                "🏠 <b>منوی اصلی</b>",
                parse_mode="HTML",
                reply_markup=main_menu(await _admin_flag(user_id)),
            )
        except Exception as exc:
            logger.error("Error filtering protocol: {}", exc)
            await query.message.reply_text(
                f"❌ <b>خطا در فیلتر!</b>\n\n{exc}",
                parse_mode="HTML",
                reply_markup=main_menu(await _admin_flag(user_id)),
            )
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
        logger.warning("Invalid count from user {}: {}", user_id, exc)
        await update.message.reply_text(
            f"❌ <b>عدد نامعتبر!</b>\n\n"
            f"📌 لطفاً عددی بین <b>{EXPORT_MIN_COUNT}</b> و <b>{EXPORT_MAX_COUNT}</b> وارد کنید.",
            parse_mode="HTML",
            reply_markup=main_menu(await _admin_flag(user_id)),
        )
        return True

    try:
        factory = get_session_factory()
        async with factory() as session:
            rows = await get_last_configs(session, count)

        if not rows:
            await update.message.reply_text(
                "❌ <b>کانفیگی یافت نشد!</b>\n\n"
                "⚠️ هنوز کانفیگی در دیتابیس ثبت نشده است.",
                parse_mode="HTML",
                reply_markup=main_menu(await _admin_flag(user_id)),
            )
            return True

        path = _build_export_file(rows, f"custom_{count}")
        with open(path, "rb") as doc:
            await update.message.reply_document(
                document=doc,
                caption=f"📦 <b>{len(rows)} کانفیگ</b>",
                parse_mode="HTML",
            )
        await update.message.reply_text(
            "✅ <b>کانفیگ‌ها با موفقیت ارسال شد!</b>",
            parse_mode="HTML",
            reply_markup=main_menu(await _admin_flag(user_id)),
        )
        logger.info("User {} received {} configs", user_id, count)
    except Exception as exc:
        logger.error("Error sending custom configs to user {}: {}", user_id, exc)
        await update.message.reply_text(
            f"❌ <b>خطا در دریافت کانفیگ!</b>\n\n{exc}",
            parse_mode="HTML",
            reply_markup=main_menu(await _admin_flag(user_id)),
        )

    return True
