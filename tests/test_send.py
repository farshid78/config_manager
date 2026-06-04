import asyncio
from telegram import Bot
from config.config import settings


async def main():

    bot = Bot(token=settings.BOT_TOKEN)

    await bot.send_message(
        chat_id="@jojo_config",
        text="🔥 BOT CONNECTED SUCCESSFULLY"
    )

    print("sent")


asyncio.run(main())