# processor/parser.py — پارس و واترمارک واقعی کانفیگ‌ها

from __future__ import annotations

import base64
import json
import re
from html import unescape

from constants import CONFIG_PATTERN
from core.config import get_settings
from core.utils import detect_protocol, extract_configs_from_text, extract_host, get_flag


class ConfigParser:
    """استخراج و واترمارک کانفیگ‌های V2Ray."""

    def extract_from_html(self, html: str) -> list[str]:
        """حذف تگ HTML و استخراج کانفیگ."""
        text = re.sub(r"<[^>]+>", "", html)
        text = unescape(text).strip()
        return extract_configs_from_text(text)

    def extract_from_text(self, text: str) -> list[str]:
        return extract_configs_from_text(text)

    def inject_watermark(self, config: str, country_code: str = "UN") -> str:
        """
        واترمارک واقعی:
        - vmess: decode Base64 → تغییر فیلد ps → encode
        - سایر: تغییر fragment (#remark)
        """
        settings = get_settings()
        channel = settings.channel_username.lstrip("@")
        flag = get_flag(country_code)
        watermark = f"[{flag}]t.me/{channel}"

        if config.startswith("vmess://"):
            return self._watermark_vmess(config, watermark)

        base = config.split("#")[0].strip()
        return f"{base}#{watermark}"

    def _watermark_vmess(self, config: str, watermark: str) -> str:
        try:
            raw = config[len("vmess://") :].strip()
            padding = len(raw) % 4
            if padding:
                raw += "=" * (4 - padding)
            data = json.loads(base64.b64decode(raw).decode("utf-8"))
            data["ps"] = watermark
            encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
            return f"vmess://{encoded}"
        except Exception:
            base = config.split("#")[0].strip()
            return f"{base}#{watermark}"

    def parse_metadata(self, config: str) -> dict:
        """متادیتای کانفیگ برای ذخیره در DB."""
        return {
            "protocol": detect_protocol(config),
            "host": extract_host(config),
        }
