# constants.py — مقادیر ثابت سراسری پروژه

# پروتکل‌های پشتیبانی‌شده
PROTOCOLS: tuple[str, ...] = ("vless", "vmess", "trojan", "shadowsocks")

# نگاشت کد کشور به برچسب نمایشی در منو
COUNTRY_LABELS: dict[str, str] = {
    "IR": "🇮🇷 Iran",
    "US": "🇺🇸 USA",
    "DE": "🇩🇪 Germany",
    "NL": "🇳🇱 Netherlands",
    "AE": "🇦🇪 UAE",
}

# پرچم کشورها برای واترمارک
COUNTRY_FLAGS: dict[str, str] = {
    "IR": "🇮🇷",
    "US": "🇺🇸",
    "DE": "🇩🇪",
    "CN": "🇨🇳",
    "AE": "🇦🇪",
    "NL": "🇳🇱",
    "NZ": "🇳🇿",
    "FI": "🇫🇮",
}

# regex استخراج کانفیگ از متن/HTML
CONFIG_PATTERN: str = (
    r"(vmess://[^\s]+|"
    r"vless://[^\s]+|"
    r"trojan://[^\s]+|"
    r"ss://[^\s]+)"
)

# محدودیت‌های export
EXPORT_MIN_COUNT = 1
EXPORT_MAX_COUNT = 10_000
EXPORT_DEFAULT_LAST = 10

# تنظیمات publisher
PUBLISH_BATCH_SIZE = 3
PUBLISH_DELAY_SECONDS = 2.2
PUBLISH_BATCH_PAUSE_SECONDS = 6.0
PUBLISH_MAX_RETRIES = 5

# تنظیمات scraper
SCRAPER_INTERVAL_SECONDS = 300
SCRAPER_PUBLISH_LIMIT = 20

# ping validation
PING_TIMEOUT_SECONDS = 4.0
