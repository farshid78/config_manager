# app/handlers/router.py

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.menus_refactor import main_menu
from app.handlers import admin, user
from app.middlewares.auth import is_admin
from database.session import get_session_factory


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id

        if await admin.admin_callback(update, context):
            return
        if await user.user_callback(update, context):
            return

        factory = get_session_factory()
        async with factory() as session:
            admin_flag = await is_admin(session, user_id)
        await query.edit_message_text(
            "\u2753 گزینه نامعتبر!\n\nاز منوی زیر استفاده کنید:",
            parse_mode="HTML",
            reply_markup=main_menu(admin_flag),
        )
    except Exception as e:
        # مدیریت خطاهای شبکه و اتصال
        error_msg = str(e)
        if "ReadError" in error_msg or "NetworkError" in error_msg or "ConnectionError" in error_msg:
            # اگر خطا مربوط به شبکه است، یک پیام مناسب نمایش می‌دهیم
            if query:
                try:
                    await query.edit_message_text(
                        "\u26a0\ufe0f خطای شبکه!\n\nلطفا اتصال اینترنت خود را بررسی کرده و دوباره امتحان کنید.",
                        parse_mode="HTML"
                    )
                except:
                    # اگر حتی ویرایش پیام هم ممکن نیست، فقط لاگ می‌کنیم
                    print(f"Network error occurred: {error_msg}")
        else:
            # برای سایر خطاها، لاگ می‌کنیم
            print(f"Error in callback_router: {error_msg}")


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id

        if await user.handle_user_text(update, context):
            return
        if await admin.handle_admin_text(update, context):
            return

        factory = get_session_factory()
        async with factory() as session:
            admin_flag = await is_admin(session, user_id)
        await update.message.reply_text(
            "از منوی زیر استفاده کنید:",
            parse_mode="HTML",
            reply_markup=main_menu(admin_flag),
        )
    except Exception as e:
        # مدیریت خطاهای شبکه و اتصال
        error_msg = str(e)
        if "ReadError" in error_msg or "NetworkError" in error_msg or "ConnectionError" in error_msg:
            # اگر خطا مربوط به شبکه است، یک پیام مناسب نمایش می‌دهیم
            try:
                await update.message.reply_text(
                    "\u26a0\ufe0f خطای شبکه!\n\nلطفا اتصال اینترنت خود را بررسی کرده و دوباره امتحان کنید.",
                    parse_mode="HTML"
                )
            except:
                # اگر ارسال پیام هم ممکن نیست، فقط لاگ می‌کنیم
                print(f"Network error occurred: {error_msg}")
        else:
            # برای سایر خطاها، لاگ می‌کنیم
            print(f"Error in message_router: {error_msg}")