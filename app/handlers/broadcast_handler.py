# app/handlers/broadcast_handler.py

from telegram import Update
from telegram.ext import ContextTypes

from app.admin_manager import is_admin
from database.database_manager import DatabaseManager


db = DatabaseManager()


async def broadcast_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not is_admin(user.id):

        await update.message.reply_text(
            "⛔ شما دسترسی ادمین ندارید."
        )

        return

    if len(context.args) == 0:

        await update.message.reply_text(
            "استفاده:\n/broadcast پیام شما"
        )

        return

    message = " ".join(context.args)

    users = db.get_all_users()

    success = 0

    for row in users:

        user_id = row[0]

        try:

            await context.bot.send_message(
                chat_id=user_id,
                text=message
            )

            success += 1

        except Exception:
            pass

    await update.message.reply_text(
        f"✅ پیام برای {success} کاربر ارسال شد."
    )