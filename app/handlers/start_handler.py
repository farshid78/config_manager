from telegram import (
    Update,
    ReplyKeyboardMarkup
)
from telegram.ext import ContextTypes

from app.user_manager import register_user
from app.logger import write_log
from app.handlers.menus.main_menu import main_menu


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    # ثبت کاربر
    register_user(user)

    # لاگ
    write_log(
        user_id=user.id,
        command="/start"
    )

    message = (
        f"سلام {user.first_name} 👋\n\n"
        f"به ربات Config Manager خوش آمدید.\n\n"
        f"از منوی زیر گزینه مورد نظر را انتخاب کنید 👇"
    )

    # منوی دائمی پایین تلگرام
    persistent_keyboard = ReplyKeyboardMarkup(
        [
            ["🏠 منوی اصلی"],
            ["🌍 کشورها", "⚙️ پروتکل‌ها"],
            ["📦 آخرین کانفیگ‌ها", "🔢 تعداد دلخواه"]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

    if update.message:

        await update.message.reply_text(
            text=message,
            reply_markup=persistent_keyboard
        )

        await update.message.reply_text(
            text="📋 منوی اصلی",
            reply_markup=main_menu(user.id)
        )

    else:

        await update.effective_chat.send_message(
            text=message,
            reply_markup=persistent_keyboard
        )

        await update.effective_chat.send_message(
            text="📋 منوی اصلی",
            reply_markup=main_menu(user.id)
        )