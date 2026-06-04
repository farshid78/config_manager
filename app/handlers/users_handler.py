# app/handlers/users_handler.py

from telegram import Update
from telegram.ext import ContextTypes

from app.admin_manager import is_admin
from database.database_manager import DatabaseManager


db = DatabaseManager()


async def users_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_admin(user.id):

        await update.message.reply_text(
            "⛔ شما دسترسی ادمین ندارید."
        )

        return

    users_count = db.get_users_count()

    await update.message.reply_text(
        f"👥 تعداد کاربران ثبت شده:\n\n{users_count}"
    )