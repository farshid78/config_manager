import pytest
from core.utils import (
    detect_protocol,
    extract_host,
    extract_port,
    config_hash,
)


def test_detect_protocol():
    """تست تشخیص پروتکل."""
    assert detect_protocol("vless://test") == "vless"
    assert detect_protocol("vmess://test") == "vmess"
    assert detect_protocol("trojan://test") == "trojan"
    assert detect_protocol("ss://test") == "shadowsocks"
    assert detect_protocol("unknown://test") == "unknown"


def test_extract_host():
    """تست استخراج host."""
    # vless format
    config = "vless://id@example.com:443?security=tls"
    assert extract_host(config) == "example.com"
    
    # trojan format
    config = "trojan://pass@example.com:443"
    assert extract_host(config) == "example.com"


def test_extract_port():
    """تست استخراج port."""
    # vless/trojan format
    config = "vless://id@example.com:8443"
    assert extract_port(config) == 8443
    
    config = "trojan://pass@example.com:443"
    assert extract_port(config) == 443


def test_config_hash():
    """تست hashing کانفیگ."""
    config1 = "vless://test#remark1"
    config2 = "vless://test#remark2"
    
    # hash باید برای base یکسان باشد (fragment نادیده گرفته می‌شود)
    assert config_hash(config1) == config_hash(config2)


def test_is_valid_ip():
    """تست تصدیق IP."""
    from app.handlers.admin import _is_valid_ip
    
    assert _is_valid_ip("192.168.1.1") is True
    assert _is_valid_ip("127.0.0.1") is True
    assert _is_valid_ip("256.1.1.1") is False
    assert _is_valid_ip("192.168.1") is False
    assert _is_valid_ip("not.an.ip.addr") is False
