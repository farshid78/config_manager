# processor/parser.py — پارس و واترمارک کانفیگ‌های V2Ray
# این ماژول کانفیگ‌ها را از متن/HTML استخراج کرده و واترمارک کانال را اضافه می‌کند

from __future__ import annotations

import base64
import json
import re
from html import unescape
from urllib.parse import quote

from constants import CONFIG_PATTERN
from core.config import get_settings
from core.utils import detect_protocol, extract_configs_from_text, extract_host, get_flag


class ConfigParser:
    """کلاس پارس و واترمارک کانفیگ‌های V2Ray.

    مسئولیت‌ها:
    - استخراج کانفیگ‌ها از HTML یا متن خام
    - تزریق واترمارک کانال به کانفیگ‌ها
    - استخراج متادیتای کانفیگ (پروتکل، host)
    """

    def extract_from_html(self, html: str) -> list[str]:
        """حذف تگ‌های HTML و استخراج کانفیگ‌ها از متن.

        ابتدا تگ‌های HTML حذف می‌شوند، سپس موجودیت‌های HTML
        (مثل &amp;) به کاراکتر تبدیل می‌شوند و در نهایت
        کانفیگ‌ها با regex استخراج می‌شوند.

        Args:
            html: متن HTML حاوی کانفیگ‌ها
        Returns:
            لیست رشته‌های کانفیگ
        """
        text = re.sub(r"<[^>]+>", "", html)  # حذف تمام تگ‌های HTML
        text = unescape(text).strip()  # تبدیل موجودیت‌های HTML و حذف فاصله
        return extract_configs_from_text(text)  # استخراج کانفیگ‌ها با regex

    def extract_from_text(self, text: str) -> list[str]:
        """استخراج کانفیگ‌ها از متن خام (بدون HTML).

        Args:
            text: متن حاوی کانفیگ‌ها
        Returns:
            لیست رشته‌های کانفیگ
        """
        return extract_configs_from_text(text)  # استخراج مستقیم با regex

    def inject_watermark(self, config: str, country_code: str = "UN") -> str:
        """تزریق واترمارک کانال به کانفیگ.

        واترمارک شامل پرچم کشور و لینک کانال تلگرام است.
        فرمت: [🇮🇷]t.me/jojo_config

        - vmess: رمزگشایی Base64 → تغییر فیلد ps → رمزگذاری مجدد
        - سایر پروتکل‌ها: تغییر fragment (#remark)

        Args:
            config: رشته کانفیگ V2Ray
            country_code: کد کشور دو حرفی (پیش‌فرض: UN)
        Returns:
            کانفیگ با واترمارک
        """
        settings = get_settings()
        channel = settings.channel_username.lstrip("@")
        flag = get_flag(country_code)
        watermark = f"{flag} t.me/{channel}"

        if config.startswith("vmess://"):
            return self._watermark_vmess(config, watermark)

        # سایر پروتکل‌ها: جایگزینی fragment با واترمارک URL-encoded
        base = config.split("#")[0].strip()
        encoded_watermark = quote(watermark, safe="")
        return f"{base}#{encoded_watermark}"

    def _watermark_vmess(self, config: str, watermark: str) -> str:
        """تزریق واترمارک به کانفیگ vmess با رمزگشایی Base64.

        مراحل:
        1. حذف پیشوند vmess://
        2. رمزگشایی Base64
        3. پارس JSON
        4. تغییر فیلد ps (remark) به واترمارک
        5. رمزگذاری مجدد

        در صورت خطا، واترمارک به صورت fragment اضافه می‌شود (fallback).

        Args:
            config: رشته کانفیگ vmess
            watermark: متن واترمارک
        Returns:
            کانفیگ vmess با واترمارک
        """
        try:
            raw = config[len("vmess://") :].strip()  # حذف پیشوند
            padding = len(raw) % 4  # محاسبه padding Base64
            if padding:  # اگر padding لازم بود
                raw += "=" * (4 - padding)  # اضافه کردن =
            data = json.loads(base64.b64decode(raw).decode("utf-8"))  # رمزگشایی و پارس
            data["ps"] = watermark  # تغییر فیلد ps (remark)
            encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()  # رمزگذاری مجدد
            return f"vmess://{encoded}"  # بازگرداندن کانفیگ واترمارک‌شده
        except Exception:
            base = config.split("#")[0].strip()
            encoded_watermark = quote(watermark, safe="")
            return f"{base}#{encoded_watermark}"

    def parse_metadata(self, config: str) -> dict:
        """استخراج متادیتای کانفیگ برای ذخیره در دیتابیس.

        Args:
            config: رشته کانفیگ V2Ray
        Returns:
            دیکشنری شامل پروتکل و آدرس سرور
        """
        return {
            "protocol": detect_protocol(config),  # نوع پروتکل (vless, vmess, ...)
            "host": extract_host(config),  # آدرس سرور (host)
        }
