# app/handlers/start_handler.py

from telegram import Update
from telegram.ext import ContextTypes

from app.user_manager import register_user


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    دستور شروع ربات
    """

    user = update.effective_user

    # ثبت کاربر در دیتابیس
    register_user(user)

    message = (
        f"سلام {user.first_name} 👋\n\n"
        f"به ربات Config Manager خوش آمدید."
    )

    await update.message.reply_text(message)