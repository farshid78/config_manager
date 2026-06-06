# core/utils.py — توابع کمکی مشترک (استخراج host، پروتکل، geo)

from __future__ import annotations

import asyncio
import base64
import json
import re
import socket
from typing import Optional

import aiohttp

from constants import COUNTRY_FLAGS, CONFIG_PATTERN

# Rate limiting for geo API
_geo_call_count = 0
_geo_last_reset = 0
_GEO_LIMIT_PER_MINUTE = 60
_geo_lock = asyncio.Lock()


def detect_protocol(config: str) -> str:
    """تشخیص نوع پروتکل از prefix کانفیگ."""
    lowered = config.lower().strip()
    if lowered.startswith("vless://"):
        return "vless"
    if lowered.startswith("vmess://"):
        return "vmess"
    if lowered.startswith("trojan://"):
        return "trojan"
    if lowered.startswith("ss://"):
        return "shadowsocks"
    return "unknown"


def extract_host(config: str) -> Optional[str]:
    """استخراج host از انواع کانفیگ V2Ray."""
    try:
        config = config.strip()

        if config.startswith(("vless://", "trojan://", "ss://")):
            match = re.search(r"@([^:]+):", config)
            if match:
                return match.group(1)

        if config.startswith("vmess://"):
            raw = config[len("vmess://") :].strip()
            padding = len(raw) % 4
            if padding:
                raw += "=" * (4 - padding)
            decoded = base64.b64decode(raw)
            data = json.loads(decoded.decode("utf-8", errors="ignore"))
            return data.get("add")

    except Exception:
        pass

    return None


def extract_port(config: str) -> Optional[int]:
    """استخراج پورت از کانفیگ."""
    try:
        if config.startswith("vmess://"):
            raw = config[len("vmess://") :].strip()
            padding = len(raw) % 4
            if padding:
                raw += "=" * (4 - padding)
            data = json.loads(base64.b64decode(raw).decode("utf-8", errors="ignore"))
            port = data.get("port")
            return int(port) if port else None

        match = re.search(r":(\d+)(?:\?|#|$|/)", config)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return None


def extract_configs_from_text(text: str) -> list[str]:
    """استخراج تمام کانفیگ‌ها از متن/HTML."""
    return re.findall(CONFIG_PATTERN, text)


def resolve_host_ip(host: str) -> Optional[str]:
    """تبدیل hostname به IP با socket sync (fallback)."""
    try:
        return socket.gethostbyname(host)
    except Exception:
        return None


async def fetch_country_code(host_or_ip: str, session: aiohttp.ClientSession) -> str:
    """دریافت کد کشور از ip-api.com با rate limiting."""
    global _geo_call_count, _geo_last_reset

    async with _geo_lock:
        import time
        now = time.time()
        if now - _geo_last_reset > 60:
            _geo_call_count = 0
            _geo_last_reset = now

        if _geo_call_count >= _GEO_LIMIT_PER_MINUTE:
            await asyncio.sleep(0.5)
            _geo_call_count = 0
            _geo_last_reset = time.time()
        _geo_call_count += 1

    try:
        ip = host_or_ip
        if not host_or_ip.replace(".", "").isdigit():
            resolved = resolve_host_ip(host_or_ip)
            if resolved:
                ip = resolved

        url = f"http://ip-api.com/json/{ip}?fields=countryCode"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("countryCode", "UN")
            return "UN"
    except Exception:
        return "UN"


def get_flag(country_code: str) -> str:
    """برگرداندن emoji پرچم از کد کشور."""
    return COUNTRY_FLAGS.get(country_code.upper(), "🏳️")


def config_hash(config: str) -> str:
    """هش ساده برای deduplication."""
    import hashlib

    normalized = config.split("#")[0].strip()
    return hashlib.md5(normalized.encode()).hexdigest()
