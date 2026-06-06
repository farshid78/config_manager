from processor.parser import ConfigParser


def test_vmess_watermark_changes_ps():
    parser = ConfigParser()
    import base64
    import json

    data = {"v": "2", "ps": "old", "add": "1.1.1.1", "port": "443", "id": "x", "aid": "0", "net": "tcp", "type": "none", "host": "", "path": "", "tls": ""}
    encoded = base64.b64encode(json.dumps(data).encode()).decode()
    config = f"vmess://{encoded}"

    result = parser.inject_watermark(config, "US")
    assert result.startswith("vmess://")
    raw = result[len("vmess://") :]
    decoded = json.loads(base64.b64decode(raw + "==").decode())
    assert "t.me/" in decoded["ps"]
