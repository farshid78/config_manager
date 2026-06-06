# app/handlers/router.py — مسیریاب مرکزی callback و message

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.menus_refactor import main_menu
from app.handlers import admin, user
from app.middlewares.auth import is_admin
from database.session import get_session_factory


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
    await query.edit_message_text("❓ گزینه نامعتبر", reply_markup=main_menu(admin_flag))


async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if await user.handle_user_text(update, context):
        return
    if await admin.handle_admin_text(update, context):
        return

    factory = get_session_factory()
    async with factory() as session:
        admin_flag = await is_admin(session, user_id)
    await update.message.reply_text(
        "از منوی زیر استفاده کنید 👇",
        reply_markup=main_menu(admin_flag),
    )
