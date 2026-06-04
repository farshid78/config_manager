# app/bot.py

from telegram.ext import (
    Application,
    CommandHandler
)

from config.config import settings

from app.handlers.start_handler import (
    start_command
)


def create_bot():

    app = Application.builder() \
        .token(settings.BOT_TOKEN) \
        .build()

    app.add_handler(
        CommandHandler(
            "start",
            start_command
        )
    )

    return app


def run_bot():

    application = create_bot()

    print("Bot Started...")

    application.run_polling()