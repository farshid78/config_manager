# app/handlers/logs_handler.py

from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from app.admin_manager import is_admin


BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOG_FILE = (
    BASE_DIR /
    "storage" /
    "logs" /
    "bot.log"
)


async def logs_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_admin(user.id):

        await update.message.reply_text(
            "⛔ شما دسترسی ادمین ندارید."
        )

        return

    if not LOG_FILE.exists():

        await update.message.reply_text(
            "هیچ لاگی وجود ندارد."
        )

        return

    with open(
        LOG_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        lines = file.readlines()

    last_lines = lines[-15:]

    text = (
        "📋 آخرین فعالیت‌ها\n\n"
        + "".join(last_lines)
    )

    await update.message.reply_text(text)