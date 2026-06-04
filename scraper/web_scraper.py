import re
import requests

from bs4 import BeautifulSoup

from database.database_manager import DatabaseManager
from utils.extractor import extract_host
from utils.geo import GeoIP
from utils.protocol import detect_protocol


class WebScraper:

    def __init__(self):

        self.db = DatabaseManager()

        self.geo = GeoIP()

        self.pattern = (
            r"(vmess://[^\s]+|"
            r"vless://[^\s]+|"
            r"trojan://[^\s]+|"
            r"ss://[^\s]+)"
        )

    def fetch_channel(self, channel: str):

        url = f"https://t.me/s/{channel}"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        return response.text

    def parse(self, html: str):

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        messages = soup.find_all(
            "div",
            class_="tgme_widget_message_text"
        )

        configs = []

        for msg in messages:

            text = msg.get_text()

            found = re.findall(
                self.pattern,
                text
            )

            configs.extend(found)

        return configs

    def save(self, configs, source):

        for config in configs:

            try:

                if self.db.get_cache(config):
                    continue

                host = extract_host(config)

                if host:
                    country = self.geo.get_country_code(host)
                else:
                    country = "UN"

                protocol = detect_protocol(config)

                print(
                    f"[SAVE] "
                    f"{country} | "
                    f"{protocol} | "
                    f"{host}"
                )

                self.db.save_processed_data(
                    input_text=config,
                    output_text=country,
                    created_at=source,
                    country_code=country,
                     protocol=protocol,
                    host=host
                )

                self.db.set_cache(
                    config,
                    "1",
                    source
                )

            except Exception as e:

                print(
                    f"[SAVE ERROR] {e}"
                )

    def run(self, channel: str):

        html = self.fetch_channel(channel)

        configs = self.parse(html)

        self.save(
            configs,
            channel
        )

        return len(configs)