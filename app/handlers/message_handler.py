from telegram import Update
from telegram.ext import ContextTypes
from config.admin_store import load_admins, save_admins
from config.admin_manager import is_admin
from database.database_manager import DatabaseManager
from app.handlers.menus.main_menu import main_menu
from datetime import datetime
import os
from pathlib import Path

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    user_id = update.effective_user.id

    # =========================
    # ADD ADMIN FLOW
    # =========================
    if context.user_data.get("awaiting_admin_id"):

        context.user_data["awaiting_admin_id"] = False

        try:
            new_admin_id = int(text)

            admins = load_admins()

            if new_admin_id in admins:

                await update.message.reply_text(
                f"✅ ادمین جدید اضافه شد:\n{new_admin_id}",
                reply_markup=main_menu(user_id)
                )
                return

            admins.add(new_admin_id)
            save_admins(admins)

            await update.message.reply_text(
                f"✅ ادمین جدید اضافه شد:\n{new_admin_id}",
                reply_markup=main_menu(user_id)
            )

        except Exception:

            await update.message.reply_text(
                "❌ آیدی نامعتبر است",
                reply_markup=main_menu(user_id)
            )

        return

    # =========================
    # ADD VIP FLOW
    # =========================
    if context.user_data.get("awaiting_vip_id"):

        context.user_data.pop("awaiting_vip_id", None)
        context.user_data.pop("awaiting_vip_remove", None)

        try:

            vip_id = int(text)

            db = DatabaseManager()

            db.add_vip_user(
                vip_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            await update.message.reply_text(
                 f"✅ کاربر {vip_id} به لیست VIP اضافه شد",
                 reply_markup=main_menu(user_id)
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ خطا",
                reply_markup=main_menu(user_id)
                )

        return

    # =========================
    # REMOVE VIP FLOW
    # =========================
    if context.user_data.get("awaiting_vip_remove"):

        context.user_data.pop("awaiting_vip_remove", None)
        context.user_data.pop("awaiting_vip_id", None)

        try:

            vip_id = int(text)

            db = DatabaseManager()

            db.remove_vip_user(vip_id)

            await update.message.reply_text(
                f"✅ کاربر {vip_id} از لیست VIP حذف شد",
                reply_markup=main_menu(user_id)
            )

        except Exception as e:

            await update.message.reply_text(
                "❌ خطا",
                reply_markup=main_menu(user_id)
                )

        return

    # =========================
    # BROADCAST FLOW
    # =========================
    if context.user_data.get("broadcast_mode"):

        context.user_data["broadcast_mode"] = False

        db = DatabaseManager()
        users = db.get_all_users()

        sent = 0

        for (uid,) in users:

            try:

                await context.bot.send_message(
                    chat_id=uid,
                    text=text
                )

                sent += 1

            except Exception:
                pass

        await update.message.reply_text(
             f"✅ پیام برای {sent} کاربر ارسال شد",
            reply_markup=main_menu(user_id)
        )

        return

    # =========================
    # CLEAN IP UPLOAD
    # =========================
    if context.user_data.get("awaiting_clean_ip"):

        if not update.message.document:

            await update.message.reply_text(
                "📄 لطفا فایل txt ارسال کنید",
                reply_markup=main_menu(user_id)
            )

            return

        document = update.message.document

        if not document.file_name.endswith(".txt"):

            await update.message.reply_text(
                "❌ فقط فایل txt مجاز است",
                reply_markup=main_menu(user_id)
            )

            return

        file = await document.get_file()

        os.makedirs("storage/clean_ips", exist_ok=True)

        file_path = (
            f"storage/clean_ips/"
            f"{document.file_name}"
        )

        await file.download_to_drive(file_path)

        db = DatabaseManager()

        db.delete_old_clean_ips()

        count = 0

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            for line in f:

                ip = line.strip()

                if not ip:
                    continue

                db.add_clean_ip(
                    ip,
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                count += 1

        context.user_data.pop(
            "awaiting_clean_ip",
            None
        )

        await update.message.reply_text(
            f"✅ {count} IP ذخیره شد",
            reply_markup=main_menu(user_id)
        )

        return

    # =========================
    # UNKNOWN MESSAGE
    # =========================
    await update.message.reply_text(
        "از منوی زیر استفاده کنید 👇",
        reply_markup=main_menu(user_id)
    )