# app/handlers/admin_handler.py

from telegram import Update
from telegram.ext import ContextTypes

from config.admin_manager import is_admin


async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user or not is_admin(user.id):

        if update.message:
            await update.message.reply_text(
                "⛔ شما دسترسی ادمین ندارید."
            )
        else:
            await update.effective_chat.send_message(
                "⛔ شما دسترسی ادمین ندارید."
            )

        return

    text = (
        "🛠 پنل مدیریت\n\n"
        "👥 کاربران\n"
        "/users\n\n"
        "📊 آمار\n"
        "/stats\n\n"
        "📢 ارسال همگانی\n"
        "/broadcast پیام\n\n"
        "📋 لاگ‌ها\n"
        "/logs\n\n"
        "✨ نسخه منوی شیشه‌ای هم از /start در دسترس است"
    )

    if update.message:
        await update.message.reply_text(text)
    else:
        await update.effective_chat.send_message(text)