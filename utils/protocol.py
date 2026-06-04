def detect_protocol(config: str):

    config = config.lower()

    if config.startswith("vless://"):
        return "vless"

    if config.startswith("vmess://"):
        return "vmess"

    if config.startswith("trojan://"):
        return "trojan"

    if config.startswith("ss://"):
        return "shadowsocks"

    return "unknown"