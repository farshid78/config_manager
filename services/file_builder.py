import os
from datetime import datetime

from utils.extractor import extract_host
from utils.geo import GeoIP

class FileBuilder:
    def __init__(self):
        self.geo = GeoIP()

    def inject_watermark(self, config):
        print("WATERMARK FUNCTION RUNNING")
        try:
            host = extract_host(config)
            flag = "🏳️"
            if host:
                flag = self.geo.get_flag(host)
            base = config.split("#")[0].strip()
            return f"{base}#[{flag}]t.me/jojo_config"
        except Exception:
            return config

    def build_txt(self, rows, filename="configs"):
        os.makedirs(
            "exports",
            exist_ok=True
        )
        path = (
            f"exports/"
            f"{filename}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            f".txt"
        )
        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:
            for row in rows:
                config = row[0] if row else ""
                config = self.inject_watermark(config)
                f.write(config + "\n\n")
        return path

