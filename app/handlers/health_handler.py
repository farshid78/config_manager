from telegram import Update
from telegram.ext import ContextTypes

from database.database_manager import DatabaseManager


db = DatabaseManager()


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        users = db.get_users_count()
        starts = db.get_total_starts()

        await update.message.reply_text(
            "🟢 SYSTEM HEALTH OK\n\n"
            f"👥 Users: {users}\n"
            f"🚀 Starts: {starts}\n"
            f"🟢 Database: OK\n"
            f"🟢 Bot: Running"
        )

    except Exception as e:

        await update.message.reply_text(
            f"🔴 SYSTEM ERROR:\n{str(e)}"
        )