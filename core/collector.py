# core/collector.py

from datetime import datetime


class DataCollector:
    """
    جمع‌آوری داده خام از منابع مختلف
    """

    def __init__(self):

        self.buffer = []

    def add_text(self, text: str):
        """
        افزودن متن ساده
        """

        item = {
            "type": "text",
            "data": text,
            "created_at": datetime.now().isoformat()
        }

        self.buffer.append(item)

        return item

    def add_url(self, url: str):
        """
        افزودن لینک
        """

        item = {
            "type": "url",
            "data": url,
            "created_at": datetime.now().isoformat()
        }

        self.buffer.append(item)

        return item

    def add_html(self, html: str):
        """
        افزودن HTML خام
        """

        item = {
            "type": "html",
            "data": html,
            "created_at": datetime.now().isoformat()
        }

        self.buffer.append(item)

        return item

    def get_all(self):
        """
        دریافت همه داده‌های جمع‌آوری‌شده
        """

        return self.buffer

    def clear(self):
        """
        پاک کردن حافظه موقت
        """

        self.buffer = []