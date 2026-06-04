from scraper.auto_scraper import AutoScraper
from app.bot import run_bot
import threading
import time


def start_bot():
    print("🤖 Bot starting...")
    run_bot()


def start_scraper():

    print("🚀 Scraper starting...")

    scraper = AutoScraper(interval=300)
    scraper.start()


if __name__ == "__main__":

    # -----------------------
    # BOT THREAD
    # -----------------------
    bot_thread = threading.Thread(
        target=start_bot,
        daemon=True   # ✅ مهم: bot همیشه background باشه
    )
    bot_thread.start()

    # -----------------------
    # SCRAPER THREAD
    # -----------------------
    scraper_thread = threading.Thread(
        target=start_scraper,
        daemon=True
    )
    scraper_thread.start()

    # -----------------------
    # KEEP ALIVE LOOP
    # -----------------------
    print("✅ System is running...")

    try:
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("🛑 Shutting down...")
        
    from utils.clean_ip_cleanup import cleanup_old_clean_ips
    cleanup_old_clean_ips()