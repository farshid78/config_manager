from telegram import Update
from telegram.ext import ContextTypes

from app.admin_manager import is_admin
from database.database_manager import DatabaseManager


db = DatabaseManager()


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not is_admin(user.id):

        await update.message.reply_text(
            "⛔ شما دسترسی ادمین ندارید."
        )
        return

    rows = db.get_last_processed(10)

    if not rows:

        await update.message.reply_text(
            "هیچ پردازشی ثبت نشده است."
        )
        return

    text = "📊 آخرین پردازش‌ها:\n\n"

    for input_text, output_text, created_at in rows:

        text += (
            f"🕒 {created_at}\n"
            f"📥 Input: {input_text}\n"
            f"📤 Output: {output_text}\n"
            f"{'-'*30}\n"
        )

    await update.message.reply_text(text)