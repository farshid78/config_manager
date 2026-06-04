import re
import base64
import json

def extract_ip(config: str):
    try:
        config = config.strip()

        # ---------------------------
        # VLESS
        # ---------------------------
        if config.startswith("vless://"):
            match = re.search(r"@([^:]+):", config)
            if match:
                return match.group(1)

        # ---------------------------
        # TROJAN
        # ---------------------------
        if config.startswith("trojan://"):
            match = re.search(r"@([^:]+):", config)
            if match:
                return match.group(1)

        # ---------------------------
        # SHADOWSOCKS
        # ---------------------------
        if config.startswith("ss://"):
            match = re.search(r"@([^:]+):", config)
            if match:
                return match.group(1)

        # ---------------------------
        # VMESS
        # ---------------------------
        if config.startswith("vmess://"):
            encoded = config.replace(
                "vmess://",
                ""
            ).strip()

            padding = len(encoded) % 4

            if padding:
                encoded += "=" * (4 - padding)

            decoded = base64.b64decode(
                encoded
            ).decode(
                "utf-8",
                errors="ignore"
            )

            data = json.loads(decoded)

            return data.get("add")

    except Exception:
        pass

    return None
