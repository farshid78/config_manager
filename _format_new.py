    def format_message(self, config: str, country_code: str) -> str:
        from constants import COUNTRY_LABELS
        from core.utils import get_flag, detect_protocol

        safe = html.escape(config)
        flag = get_flag(country_code)
        country_name = COUNTRY_LABELS.get(country_code, country_code)
        protocol = detect_protocol(config).upper()
        channel = self.settings.channel_username.lstrip("@")

        # ساخت هدر مثل نمونه: #v2ray + پرچم و کانفیگ
        header = f"#v2ray\n{safe}"

        # بدنه با کشور و کانال‌ها
        separator = "━━━━━━━━━━━━━━━━━━━━"
        country_line = f"ᴄᴏᴜɴᴛʀʏ: #{country_name.lower()}({country_code})"
        channels = f"ᴄᴏɴғɪɢsʜᴜʙ (https://t.me/{channel}) ₪ ᴀʀɪʏₐ (https://t.me/kingariya) ₪ ʙᴏᴛ (https://t.me/ConfigsHUB_BOT) ₪ ʜᴇʟᴘ (https://t.me/ConfigsHubPlus/319648)"

        return f"{header}\n{separator}\n{country_line}\n{channels}"