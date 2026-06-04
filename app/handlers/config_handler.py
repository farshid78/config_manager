from telegram import Update
from telegram.ext import ContextTypes

from database.database_manager import DatabaseManager


db = DatabaseManager()


def format_configs(rows):

    if not rows:
        return "❌ هیچ کانفیگی پیدا نشد"

    text = "🔥 کانفیگ‌های شما:\n\n"

    for c, cat in rows:

        text += (
            f"📦 {cat}\n"
            f"{c}\n\n"
            "──────────────\n\n"
        )

    return text


async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    cmd = update.message.text.lower().replace("/", "").strip()

    if cmd == "ir":
        rows = db.get_configs_by_category("IR", 10)

    elif cmd == "us":
        rows = db.get_configs_by_category("US", 10)

    elif cmd == "de":
        rows = db.get_configs_by_category("DE", 10)

    elif cmd == "all":
        rows = db.get_configs_by_category("GLOBAL", 10)

    else:
        await update.message.reply_text("❌ دستور نامعتبر")
        return

    text = format_configs(rows)

    await update.message.reply_text(text)