from utils.extractor import extract_host
from utils.ip_resolver import resolve_host
from utils.geo import GeoIP

geo = GeoIP()

def detect_country(config: str):
    host = extract_host(config)
    if not host:
        return "UNKNOWN"

    ip = resolve_host(host)
    if not ip:
        ip = host

    try:
        return geo.get_country(ip)
    except Exception:
        return "UNKNOWN"

