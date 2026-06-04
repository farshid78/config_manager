# app/handlers/stats_handler.py

from telegram import Update
from telegram.ext import ContextTypes

from app.admin_manager import is_admin
from app.logger import write_log

from database.database_manager import DatabaseManager


db = DatabaseManager()


async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    # ثبت لاگ
    write_log(
        user.id,
        "/stats"
    )

    if not is_admin(user.id):

        await update.message.reply_text(
            "⛔ شما دسترسی ادمین ندارید."
        )

        return

    users_count = db.get_users_count()

    total_starts = db.get_total_starts()

    text = (
        "📊 آمار ربات\n\n"
        f"👥 کاربران: {users_count}\n"
        f"🚀 اجرای /start: {total_starts}"
    )

    await update.message.reply_text(text)