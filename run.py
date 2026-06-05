from scraper.auto_scraper import AutoScraper
from app.bot import create_bot
import threading
import time
import asyncio


def start_scraper():
    print("🚀 Scraper starting...")
    scraper = AutoScraper(interval=300)
    scraper.start()


if __name__ == "__main__":

    # -----------------------
    # SCRAPER THREAD (background)
    # -----------------------
    scraper_thread = threading.Thread(
        target=start_scraper,
        daemon=True
    )
    scraper_thread.start()

    # -----------------------
    # BOT (main thread)
    # -----------------------
    print("🤖 Bot starting...")
    application = create_bot()
    print("🚀 Bot Started...")
    application.run_polling()

    from utils.clean_ip_cleanup import cleanup_old_clean_ips
    cleanup_old_clean_ips()
