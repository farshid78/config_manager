# core/parser.py

import re
from html import unescape


class DataParser:
    """
    استخراج اطلاعات از داده خام
    """

    URL_PATTERN = r'https?://[^\s]+'
    EMAIL_PATTERN = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'

    def extract_urls(self, text: str):
        """
        استخراج لینک‌ها از متن
        """

        return re.findall(self.URL_PATTERN, text)

    def extract_emails(self, text: str):
        """
        استخراج ایمیل‌ها
        """

        return re.findall(self.EMAIL_PATTERN, text)

    def clean_html(self, html: str):
        """
        تبدیل HTML به متن ساده
        """

        text = re.sub(r'<[^>]+>', '', html)
        text = unescape(text)

        return text.strip()

    def extract_all(self, text: str):
        """
        استخراج همه داده‌های مهم از متن
        """

        return {
            "urls": self.extract_urls(text),
            "emails": self.extract_emails(text),
            "clean_text": self.clean_html(text)
        }