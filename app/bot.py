from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from config.config import settings

# =========================
# HANDLERS
# =========================
from app.handlers.start_handler import start_command
from app.handlers.users_handler import users_command
from app.handlers.stats_handler import stats_command
from app.handlers.logs_handler import logs_command
from app.handlers.broadcast_handler import broadcast_command
from app.handlers.admin_handler import admin_command
from app.handlers.process_handler import process_command
from app.handlers.history_handler import history_command
from app.handlers.health_handler import health_command
from app.handlers.config_handler import config_command
from app.handlers.export_handler import export_command
from app.handlers.callback import callback_handler
from app.handlers.message_handler import handle_message
from config.admin_store import load_admins

ADMINS = load_admins()

# =========================
# BOT CREATION
# =========================
def create_bot():

    application = Application.builder().token(settings.BOT_TOKEN).build()

    # ---------------- START ----------------
    application.add_handler(CommandHandler("start", start_command))

    # ---------------- ADMIN COMMANDS ----------------
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("logs", logs_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("process", process_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("health", health_command))

    # ---------------- CONFIG COMMANDS ----------------
    application.add_handler(CommandHandler("ir", config_command))
    application.add_handler(CommandHandler("us", config_command))
    application.add_handler(CommandHandler("de", config_command))
    application.add_handler(CommandHandler("all", config_command))

    # ---------------- CALLBACK MENU ----------------
    application.add_handler(CallbackQueryHandler(callback_handler))

    # ---------------- MESSAGE INPUT ----------------
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        
    )

    return application


# =========================
# RUN BOT
# =========================
def run_bot():

    application = create_bot()

    print("🚀 Bot Started...")

    application.run_polling()