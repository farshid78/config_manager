import base64
import json
import re

def extract_host(config: str):
    try:
        config = config.strip()

        if config.startswith("vless://"):
            m = re.search(r"@([^:]+):", config)
            if m:
                return m.group(1)

        if config.startswith("trojan://"):
            m = re.search(r"@([^:]+):", config)
            if m:
                return m.group(1)

        if config.startswith("ss://"):
            m = re.search(r"@([^:]+):", config)
            if m:
                return m.group(1)

        if config.startswith("vmess://"):
            raw = config[len("vmess://"):].strip()
            padding = len(raw) % 4
            if padding:
                raw += "=" * (4 - padding)

            decoded = base64.b64decode(raw)
            data = json.loads(decoded.decode("utf-8", errors="ignore"))
            return data.get("add")

    except Exception:
        pass

    return None