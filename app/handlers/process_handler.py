from telegram import Update
from telegram.ext import ContextTypes

from datetime import datetime

from core.processor import DataProcessor
from database.database_manager import DatabaseManager


processor = DataProcessor()
db = DatabaseManager()


async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:

        await update.message.reply_text(
            "استفاده:\n/process متن شما"
        )
        return

    text = " ".join(context.args)

    data = [
        {
            "type": "text",
            "data": text
        }
    ]

    result = processor.process_batch(data)

    # تبدیل خروجی به متن
    output = ""

    for item in result:
        output += f"{item}\n\n"

    # ذخیره در دیتابیس
    db.save_processed_data(
        input_text=text,
        output_text=output,
        created_at=datetime.now().isoformat()
    )

    await update.message.reply_text(
        f"📦 نتیجه پردازش:\n\n{output}"
    )