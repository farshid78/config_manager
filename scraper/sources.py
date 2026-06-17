# scraper/sources.py — منابع جمع‌آوری کانفیگ
# دو نوع منبع: کانال تلگرام (telegram) و اشتراک/سابسکریپشن (subscription)

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Source:
    """یک منبع جمع‌آوری کانفیگ.

    Attributes:
        name: نام منبع (برای لاگ و نمایش)
        url: آدرس منبع (کانال تلگرام یا لینک اشتراک)
        source_type: نوع منبع - "telegram" یا "subscription"
    """
    name: str
    url: str
    source_type: str  # "telegram" یا "subscription"


# ─── منابع کانال تلگرام ───
# فرمت: نام کانال بدون @
TELEGRAM_SOURCES: list[Source] = [
    Source(name="filembad", url="filembad", source_type="telegram"),
    Source(name="vpnine1", url="vpnine1", source_type="telegram"),
    Source(name="ConfigsHUB2", url="ConfigsHUB2", source_type="telegram"),
    Source(name="free_v2rayyy", url="free_v2rayyy", source_type="telegram"),
    Source(name="v2rayng_config", url="v2rayng_config", source_type="telegram"),
    Source(name="v2rayng_org", url="v2rayng_org", source_type="telegram"),
    Source(name="vasl_bashim", url="vasl_bashim", source_type="telegram"),
    Source(name="configs_freeiran", url="configs_freeiran", source_type="telegram"),
    Source(name="MARTiNCONFiG", url="MARTiNCONFiG", source_type="telegram"),
    Source(name="best_internet_iran", url="best_internet_iran", source_type="telegram"),
    Source(name="persianvpnhub", url="persianvpnhub", source_type="telegram"),
]

# ─── منابع اشتراک (Subscription) ───
# این منابع فایل‌های متنی حاوی کانفیگ هستند (Base64 یا متن خام)
# فرمت‌ها:
#   - لینک مستقیم raw (GitHub, shz.al و غیره)
#   - محتوا ممکن است Base64-encoded باشد
SUBSCRIPTION_SOURCES: list[Source] = [
    Source(
        name="sorenab1sub",
        url="https://shz.al/DyAii8ySZtNHAizTPf3EHzS3:/~sorenab1sub",
        source_type="subscription",
    ),
    Source(
        name="VPNine1-sub",
        url="https://raw.githubusercontent.com/vpnine1/sub/main/@VPNine1-sub836#@VPNine1-sub836",
        source_type="subscription",
    ),
    Source(
        name="Masir_Sefid",
        url="https://raw.githubusercontent.com/masir-sefid/Sub/main/@Masir_Sefid.txt",
        source_type="subscription",
    ),
]

# ─── لیست قدیمی برای سازگاری ───
SOURCES: list[str] = [s.url for s in TELEGRAM_SOURCES]

# ─── تمام منابع ───
ALL_SOURCES: list[Source] = TELEGRAM_SOURCES + SUBSCRIPTION_SOURCES
