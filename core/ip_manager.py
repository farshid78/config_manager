# core/ip_manager.py — مدیریت IP و اعمال بر روی کانفیگ‌ها

from __future__ import annotations

import re
from typing import Optional

from core.logger import get_logger
from core.utils import is_valid_ip

logger = get_logger()


def parse_ips_from_text(text: str) -> list[str]:
    """تجزیه IP‌ها از متن (یک IP در هر خط یا فاصله‌شده)."""
    ips = []
    
    # Split by newlines and commas and spaces
    candidates = re.split(r'[\n\r,\s]+', text.strip())
    
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and is_valid_ip(candidate):
            ips.append(candidate)
        elif candidate:
            logger.warning("Invalid IP format: {}", candidate)
    
    return ips


async def parse_ips_from_file(file_path: str) -> list[str]:
    """خواندن IP‌ها از فایل txt."""
    ips = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Handle multiple IPs per line
                for candidate in re.split(r'[\s,]+', line):
                    candidate = candidate.strip()
                    if candidate and is_valid_ip(candidate):
                        ips.append(candidate)
                    elif candidate:
                        logger.warning("Invalid IP in file: {}", candidate)
    except Exception as exc:
        logger.error("Error reading IP file {}: {}", file_path, exc)
        raise
    
    return ips


def apply_ip_to_config(config: str, ip: str) -> Optional[str]:
    """
    اعمال IP به کانفیگ (به‌روزرسانی host).
    
    برای VLESS/VMESS/Trojan: جایگزین کردن host
    برای SS: جایگزین کردن آدرس
    """
    try:
        # Extract base (without fragment)
        base_config = config.split("#")[0].strip()
        fragment = config.split("#")[1] if "#" in config else ""
        
        # Replace host in config
        # Pattern: @oldhost:port → @newip:port
        result = re.sub(
            r"@[^:]+:",
            f"@{ip}:",
            base_config
        )
        
        # Re-add fragment if exists
        if fragment:
            result = f"{result}#{fragment}"
        
        return result if result != base_config else None
    except Exception as exc:
        logger.error("Error applying IP {} to config: {}", ip, exc)
        return None


async def apply_ips_to_configs(
    ips: list[str],
    configs: list,  # list[ProcessedConfig]
    apply_per_ip: int = 5
) -> list[str]:
    """
    اعمال IP‌های دریافت شده به کانفیگ‌ها.
    
    برای هر IP، N بار (apply_per_ip) کانفیگ‌ها را روتیشن دهی و IP را اعمال کن.
    """
    output_configs = []
    
    if not configs:
        logger.warning("No configs to apply IPs to")
        return []
    
    for ip in ips:
        for i in range(apply_per_ip):
            # Rotate through configs
            config_row = configs[i % len(configs)]
            config_text = config_row.watermarked_config or config_row.raw_config
            
            # Apply IP to this config
            modified = apply_ip_to_config(config_text, ip)
            if modified:
                output_configs.append(modified)
            else:
                # Fallback to original if modification failed
                output_configs.append(config_text)
    
    logger.info("Applied {} IPs to {} configs, output: {} configs", 
                len(ips), len(configs), len(output_configs))
    
    return output_configs


def format_configs_as_text(configs: list[str]) -> str:
    """فرمت‌کردن کانفیگ‌های برای ارسال به صورت متن."""
    return "\n\n".join(configs)


async def cleanup_temp_files(export_dir, max_age_minutes: int = 10) -> int:
    """حذف فایل‌های موقت قدیمی‌تر از max_age_minutes."""
    from pathlib import Path
    from datetime import datetime, timedelta
    
    deleted_count = 0
    cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
    
    try:
        export_path = Path(export_dir)
        for temp_file in export_path.glob("temp_*.txt"):
            file_mtime = datetime.fromtimestamp(temp_file.stat().st_mtime)
            if file_mtime < cutoff_time:
                try:
                    temp_file.unlink()
                    deleted_count += 1
                    logger.debug("Deleted temp file: {}", temp_file.name)
                except Exception as exc:
                    logger.error("Error deleting temp file {}: {}", temp_file.name, exc)
    except Exception as exc:
        logger.error("Error during temp file cleanup: {}", exc)
    
    if deleted_count > 0:
        logger.info("Cleaned up {} temp files", deleted_count)
    
    return deleted_count
