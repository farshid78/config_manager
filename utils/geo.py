import socket
import requests

class GeoIP:
    COUNTRY_FLAGS = {
        "IR": "🇮🇷",
        "US": "🇺🇸",
        "DE": "🇩🇪",
        "CN": "🇨🇳",
        "AE": "🇦🇪",
        "NL": "🇳🇱",
        "NZ": "🇳🇿",
        "FI": "🇫🇮",
    }

    def resolve_host(self, host: str):
        try:
            return socket.gethostbyname(host)
        except Exception:
            return None

    def get_country_code(self, host_or_ip: str):
        try:
            ip = host_or_ip

            if not host_or_ip.replace(".", "").isdigit():
                resolved = self.resolve_host(host_or_ip)
                if resolved:
                    ip = resolved

            url = f"http://ip-api.com/json/{ip}"
            res = requests.get(url, timeout=5)
            data = res.json()
            return data.get("countryCode", "UN")
        except Exception:
            return "UN"

    def get_flag(self, host_or_ip: str):
        code = self.get_country_code(host_or_ip)
        return self.COUNTRY_FLAGS.get(code, "🏳️")

    def get_country(self, host_or_ip: str):
        return self.get_country_code(host_or_ip)

