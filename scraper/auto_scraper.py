from scraper.web_scraper import WebScraper
from config.sources import SOURCES
from services.publisher import Publisher
from database.database_manager import DatabaseManager
import time


class AutoScraper:

    def __init__(self, interval=300):

        self.scraper = WebScraper()
        self.publisher = Publisher()
        self.db = DatabaseManager()
        self.interval = interval

    # -----------------------
    # run scraping + store in DB
    # -----------------------
    def run_once(self):

        for source in SOURCES:

            try:
                self.scraper.run(source)
                print(f"[SCRAPED] {source}")

            except Exception as e:
                print(f"[ERROR] {source} → {e}")

        # بعد از scrape → از DB بخون
        rows = self.db.get_last_processed(20)

        # send to publisher
        sent = self.publisher.publish(rows)

        print(f"📤 Sent: {sent}")

        return sent

    # -----------------------
    # loop
    # -----------------------
    def start(self):

        print("🚀 AutoScraper Started...")

        while True:

            self.run_once()

            time.sleep(self.interval)