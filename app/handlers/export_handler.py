from telegram import Update
from telegram.ext import ContextTypes

from app.admin_manager import is_admin
from utils.export_manager import ExportManager


exporter = ExportManager()


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not is_admin(user.id):

        await update.message.reply_text("⛔ دسترسی ندارید")
        return

    if not context.args:

        await update.message.reply_text(
            "استفاده:\n/export users\n/export history"
        )
        return

    target = context.args[0]

    if target == "users":

        file = exporter.export_users_json()

    elif target == "history":

        file = exporter.export_history_json()

    else:

        await update.message.reply_text("نوع نامعتبر")
        return

    await update.message.reply_text(
        f"📤 فایل ساخته شد:\n{file}"
    )