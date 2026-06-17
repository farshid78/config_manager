# core/utils.py — توابع کمکی مشترک پروژه
# شامل: استخراج اطلاعات کانفیگ، اعتبارسنجی IP، تشخیص کشور، واترمارک و هش

from __future__ import annotations  # پشتیبانی از type hints پیشرفته

import asyncio  # عملیات ناهمزمان
import base64  # رمزگشایی Base64 (برای vmess)
import hashlib  # هش‌کردن (برای deduplication)
import ipaddress  # اعتبارسنجی آدرس IP
import json  # پارس JSON (برای vmess)
import re  # عبارات منظم (regex)
import socket  # تبدیل hostname به IP
import time  # زمان‌بندی برای rate limiter
from typing import Optional  # نوع Optional برای مقادیر ممکن None

import aiohttp  # کلاینت HTTP ناهمزمان

from constants import COUNTRY_FLAGS, CONFIG_PATTERN  # ثابت‌های پروژه


def is_valid_ip(ip: str) -> bool:
    """اعتبارسنجی آدرس IPv4.

    Args:
        ip: رشته آدرس IP برای بررسی
    Returns:
        True اگر IP معتبر باشد، False در غیر این صورت
    """
    try:
        ipaddress.IPv4Address(ip.strip())  # تلاش برای ساخت شیء IPv4
        return True  # IP معتبر است
    except Exception:  # اگر خطا رخ داد، IP نامعتبر است
        return False


def detect_protocol(config: str) -> str:
    """تشخیص نوع پروتکل از پیشوند کانفیگ.

    Args:
        config: رشته کانفیگ V2Ray
    Returns:
        نام پروتکل: vless, vmess, trojan, shadowsocks یا unknown
    """
    lowered = config.lower().strip()  # تبدیل به حروف کوچک
    if lowered.startswith("vless://"):  # پروتکل VLESS
        return "vless"
    if lowered.startswith("vmess://"):  # پروتکل VMess
        return "vmess"
    if lowered.startswith("trojan://"):  # پروتکل Trojan
        return "trojan"
    if lowered.startswith("ss://"):  # پروتکل Shadowsocks
        return "shadowsocks"
    return "unknown"  # پروتکل ناشناخته


def extract_host(config: str) -> Optional[str]:
    """استخراج آدرس host (سرور) از انواع کانفیگ V2Ray.

    برای vless/trojan/ss: از regex استخراج می‌شود
    برای vmess: از JSON رمزگشایی شده استخراج می‌شود

    Args:
        config: رشته کانفیگ V2Ray
    Returns:
        آدرس host یا None در صورت خطا
    """
    try:
        config = config.strip()  # حذف فاصله‌های اضافی

        # استخراج host از کانفیگ‌های vless/trojan/ss با regex
        if config.startswith(("vless://", "trojan://", "ss://")):
            match = re.search(r"@([^:]+):", config)  # جستجوی الگوی @host:
            if match:
                return match.group(1)  # بازگرداندن host

        # استخراج host از کانفیگ vmess (رمزگشایی Base64)
        if config.startswith("vmess://"):
            raw = config[len("vmess://") :].strip()  # حذف پیشوند
            padding = len(raw) % 4  # محاسبه padding مورد نیاز Base64
            if padding:
                raw += "=" * (4 - padding)  # اضافه کردن padding
            decoded = base64.b64decode(raw)  # رمزگشایی Base64
            data = json.loads(decoded.decode("utf-8", errors="ignore"))  # پارس JSON
            return data.get("add")  # فیلد add شامل آدرس سرور است

    except Exception:  # در صورت هر خطایی
        pass  # بی‌صدا نادیده بگیر

    return None  # بازگرداندن None در صورت عدم موفقیت


def extract_port(config: str) -> Optional[int]:
    """استخراج شماره پورت از کانفیگ.

    برای vmess: از JSON رمزگشایی شده
    برای سایر پروتکل‌ها: از regex

    Args:
        config: رشته کانفیگ V2Ray
    Returns:
        شماره پورت یا None در صورت خطا
    """
    try:
        # استخراج پورت از vmess (رمزگشایی Base64)
        if config.startswith("vmess://"):
            raw = config[len("vmess://") :].strip()  # حذف پیشوند
            padding = len(raw) % 4  # محاسبه padding
            if padding:
                raw += "=" * (4 - padding)  # اضافه کردن padding
            data = json.loads(base64.b64decode(raw).decode("utf-8", errors="ignore"))  # پارس JSON
            port = data.get("port")  # فیلد port
            return int(port) if port else None  # تبدیل به عدد صحیح

        # استخراج پورت از سایر پروتکل‌ها با regex
        match = re.search(r":(\d+)(?:\?|#|$|/)", config)  # الگوی :port
        if match:
            return int(match.group(1))  # بازگرداندن شماره پورت
    except Exception:  # در صورت خطا
        pass  # بی‌صدا نادیده بگیر
    return None  # بازگرداندن None


def extract_configs_from_text(text: str) -> list[str]:
    """استخراج تمام کانفیگ‌های V2Ray از متن یا HTML.

    از regex تعریف‌شده در CONFIG_PATTERN استفاده می‌کند.
    ابتدا HTML entities تبدیل می‌شوند تا کانفیگ‌ها درست استخراج شوند.

    Args:
        text: متن ورودی (ممکن است HTML باشد)
    Returns:
        لیست کانفیگ‌های یافت‌شده
    """
    from html import unescape
    # تبدیل HTML entities (مثل &amp; -> &)
    clean_text = unescape(text)
    return re.findall(CONFIG_PATTERN, clean_text)  # یافتن تمام تطابق‌ها


async def resolve_host_ip(host: str) -> Optional[str]:
    """تبدیل hostname به آدرس IP (ناهمزمان/async).

    از asyncio.get_event_loop().run_in_executor برای اجرای
    DNS resolution سیستمی بدون مسدود کردن event loop استفاده می‌کند.

    Args:
        host: hostname یا دامنه سرور
    Returns:
        آدرس IP یا None در صورت عدم موفقیت
    """
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, socket.gethostbyname, host)
    except Exception:  # اگر hostname قابل حل نبود
        return None


# ─── Rate Limiter برای ip-api.com ────────────────────────
# ip-api.com محدودیت 45 درخواست در دقیقه دارد

class _GeoRateLimiter:
    """Rate limiter با الگوریتم Token-bucket برای محدودسازی درخواست‌های geo API.

    از این کلاس برای رعایت محدودیت ip-api.com استفاده می‌شود.
    حداکثر calls_per_minute درخواست در دقیقه مجاز است.
    """

    def __init__(self, calls_per_minute: int = 120):
        self._calls_per_minute = calls_per_minute
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """دریافت اجازه ارسال درخواست جدید.

        اگر تعداد درخواست‌ها به حد مجاز رسیده باشد،
        صبر می‌کند تا پنجره زمانی باز شود.
        """
        async with self._lock:  # قفل برای جلوگیری از race condition
            now = time.time()  # زمان فعلی
            # پاک‌سازی timestamp‌های قدیمی‌تر از ۶۰ ثانیه
            self._timestamps = [t for t in self._timestamps if now - t < 60]

            # اگر به حد مجاز رسیدهیم، صبر کن
            if len(self._timestamps) >= self._calls_per_minute:
                oldest = self._timestamps[0]  # قدیمی‌ترین درخواست
                wait_time = 60 - (now - oldest) + 0.1  # زمان انتظار + بافر
                await asyncio.sleep(wait_time)  # صبر کردن
                self._timestamps.clear()  # پاک‌سازی لیست بعد از انتظار

            self._timestamps.append(time.time())  # ثبت زمان درخواست جدید


_geo_rate_limiter = _GeoRateLimiter()  # نمونه singleton از rate limiter


async def fetch_country_code(host_or_ip: str, session: aiohttp.ClientSession) -> str:
    """دریافت کد کشور از Geo API با رعایت rate limiting.

    از ipwhois.app (HTTPS) استفاده می‌کند که در ایران با پروکسی قابل دسترسی است.
    fallback: ip-api.com (HTTP)

    Args:
        host_or_ip: آدرس IP یا hostname سرور
        session: نشست HTTP ناهمزمان
    Returns:
        کد کشور دو حرفی (مثل "IR", "US") یا "UN" در صورت خطا
    """
    from core.config import get_settings

    await _geo_rate_limiter.acquire()

    try:
        ip = host_or_ip
        if not host_or_ip.replace(".", "").isdigit():
            resolved = await resolve_host_ip(host_or_ip)
            if resolved:
                ip = resolved

        settings = get_settings()
        proxy = settings.scraper_proxy.strip() if settings.scraper_proxy else None
        timeout = aiohttp.ClientTimeout(total=8)

        # روش 1: ipwhois.app (HTTPS — با پروکسی کار می‌کند)
        url = f"https://ipwhois.app/json/{ip}?fields=country_code"
        async with session.get(url, timeout=timeout, proxy=proxy) as resp:
            if resp.status == 200:
                data = await resp.json()
                code = data.get("country_code") or data.get("countryCode")
                if code and len(code) == 2:
                    return code.upper()

        # روش 2: fallback به ip-api.com (HTTP — بدون پروکسی)
        url2 = f"http://ip-api.com/json/{ip}?fields=countryCode"
        async with session.get(url2, timeout=timeout) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("countryCode", "UN")

        return "UN"
    except Exception:
        return "UN"


def get_flag(country_code: str) -> str:
    """برگرداندن emoji پرچم متناسب با کد کشور.

    از Regional Indicator Symbols برای ساخت پرچم استفاده می‌کند.
    هر حرف لاتین به indicator تبدیل می‌شود: A→🇦, B→🇧, ...
    بنابراین برای هر کد کشور دو حرفی پرچم ساخته می‌شود.

    Args:
        country_code: کد کشور دو حرفی (مثل "IR")
    Returns:
        emoji پرچم یا 🏳️ در صورت عدم وجود
    """
    code = country_code.upper().strip()
    if code == "UN":
        return "🏳️"  # پرچم سازمان ملل برای کدهای نامعتبر
    if len(code) == 2 and code.isalpha():
        # Regional Indicator: هر حرف + 0x1F1E5 = indicator emoji
        return chr(0x1F1E5 + ord(code[0])) + chr(0x1F1E5 + ord(code[1]))
    return "🏳️"


def config_hash(config: str) -> str:
    """محاسبه هش MD5 از کانفیگ برای تشخیص تکراری (deduplication).

    بخش remark (بعد از #) نادیده گرفته می‌شود تا کانفیگ‌های
    با remark مختلف اما سرور یکسان، تکراری شناخته شوند.

    Args:
        config: رشته کانفیگ V2Ray
    Returns:
        هش MD5 به صورت هگزادسیمال
    """
    normalized = config.split("#")[0].strip()  # حذف remark از انتها
    return hashlib.md5(normalized.encode()).hexdigest()  # محاسبه MD5


def sanitize_filename(filename: str) -> str:
    """پاک‌سازی نام فایل برای جلوگیری از حملات path traversal.

    - جایگزینی / و \\ با _
    - حذف .. (دسترسی به پوشه بالاتر)
    - حذف کاراکترهای غیرمجاز
    - محدود کردن طول نام به 120 کاراکتر

    Args:
        filename: نام فایل ورودی (از کاربر)
    Returns:
        نام فایل امن و پاک‌شده
    """
    name = re.sub(r"[\\/]+", "_", filename)  # جایگزینی اسلش با زیرخط
    name = name.replace("..", "")  # حذف دسترسی به پوشه بالاتر
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)  # حذف کاراکترهای غیرمجاز
    name = name[:120] if name else "unnamed.txt"  # محدودیت طول + نام پیش‌فرض


def generate_config(host: str = None, port: int = None, protocol: str = "vmess", country_code: str = "IR") -> dict:
    """ایجاد یک کانفیگ نمونه برای تست.

    Args:
        host: آدرس سرور (IP یا دامنه)
        port: پورت سرور (پیش‌فرض: 443)
        protocol: نوع پروتکل (پیش‌فرض: vmess)
        country_code: کد کشور (پیش‌فرض: IR)

    Returns:
        دیکشنری شامل اطلاعات کانفیگ
    """
    import uuid
    
    # تنظیم مقادیر پیش‌فرض
    if port is None:
        port = 443
    if host is None:
        host = "127.0.0.1"
    
    # ایجاد کانفیگ بر اساس پروتکل
    if protocol.lower() == "vmess":
        # ایجاد کانفیگ vmess
        uuid_str = str(uuid.uuid4())
        config = {
            "v": "2",
            "ps": f"{country_code}-{host}",
            "add": host,
            "port": str(port),
            "id": uuid_str,
            "aid": "0",
            "net": "ws",
            "type": "none",
            "host": "",
            "path": "/",
            "tls": "tls"
        }
        raw_config = f"vmess://{base64.b64encode(json.dumps(config).encode()).decode()}"
        watermarked_config = raw_config
    else:
        # ایجاد کانفیگ vless
        uuid_str = str(uuid.uuid4())
        raw_config = f"vless://{uuid_str}@{host}:{port}?encryption=none&security=tls&type=ws&host=&path=/#{country_code}-{host}"
        watermarked_config = raw_config
    
    # محاسبه هش کانفیگ
    config_hash = hashlib.md5(raw_config.encode()).hexdigest()
    
    return {
        "raw_config": raw_config,
        "watermarked_config": watermarked_config,
        "config_hash": config_hash,
        "country_code": country_code,
        "protocol": protocol,
        "host": host
    }
