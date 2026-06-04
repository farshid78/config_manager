import code
from logging import config
import time
import html
import requests

from utils.geo import GeoIP
from utils.extractor import extract_host
from config.config import settings
from config.publish_config import CHANNEL_USERNAME


class Publisher:

    def __init__(self):

        self.url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

        self.geo = GeoIP()

        self.delay_between_messages = 2.2
        self.delay_between_batches = 6
        self.batch_size = 3

    # -----------------------
    # inject watermark with country flag
    # -----------------------
    def inject_watermark(self, config: str):

        host = extract_host(config)

        flag = self.geo.get_flag(host) if host else "🏳️"

        watermark = f"[{flag}]t.me/jojo_config"

        base = config.split("#")[0].strip()

        return base + "#" + watermark

    # -----------------------
    # resolve category from IP (FIX اصلی)
    # -----------------------
    def resolve_category(self, config: str, db_category: str):


        host = extract_host(config)

        if not host:
          return db_category or "UNKNOWN"

        code = self.geo.get_country_code(host)

        return code



    # -----------------------
    # format message
    # -----------------------
    def format_config(self, config: str, category: str):

        config = self.inject_watermark(config)

        safe_config = html.escape(config)

        return (
            f"🔥 NEW CONFIG\n"
            f"📦 Category: {category}\n\n"
            f"<pre>{safe_config}</pre>"
        )

    # -----------------------
    # send message
    # -----------------------
    def send_message(self, text: str):

        response = requests.post(self.url, data={
            "chat_id": CHANNEL_USERNAME,
            "text": text,
            "parse_mode": "HTML"
        })

        if response.status_code == 429:
            retry_after = response.json().get("parameters", {}).get("retry_after", 5)
            print(f"[RATE LIMIT] sleeping {retry_after}s")
            time.sleep(retry_after)
            return self.send_message(text)

        return response

    # -----------------------
    # main publish
    # -----------------------
    def publish(self, configs):

        sent = 0

        for i in range(0, len(configs), self.batch_size):

            batch = configs[i:i + self.batch_size]

            for row in batch:

                try:
                    config = row[0]
                    db_category = row[1] if len(row) > 1 else "UNKNOWN"

                    # FIX: category from IP
                    category = self.resolve_category(config, db_category)

                    text = self.format_config(config, category)

                    response = self.send_message(text)

                    if response.status_code == 200:
                        sent += 1
                        print("[OK] sent")
                    else:
                        print("Telegram error:", response.text)

                    time.sleep(self.delay_between_messages)

                except Exception as e:
                    print(f"Publish error: {e}")

            print("[BATCH DONE]")
            time.sleep(self.delay_between_batches)

        return sent