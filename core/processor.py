# core/processor.py

from core.parser import DataParser
from core.deduplicator import Deduplicator


class DataProcessor:
    """
    پردازش کامل داده‌ها (Pipeline اصلی)
    """

    def __init__(self):

        self.parser = DataParser()
        self.deduplicator = Deduplicator()

    def process(self, data: dict):
        """
        پردازش یک آیتم داده خام
        """

        raw_text = data.get("data", "")
        data_type = data.get("type", "")

        result = {
            "type": data_type,
            "original": raw_text,
            "parsed": None
        }

        # پردازش بر اساس نوع داده
        if data_type == "text":

            parsed = self.parser.extract_all(raw_text)

        elif data_type == "html":

            parsed = self.parser.extract_all(
                self.parser.clean_html(raw_text)
            )

        elif data_type == "url":

            parsed = {
                "urls": [raw_text],
                "emails": [],
                "clean_text": raw_text
            }

        else:

            parsed = {
                "urls": [],
                "emails": [],
                "clean_text": raw_text
            }

        result["parsed"] = parsed

        return result

    def process_batch(self, items: list):
        """
        پردازش لیستی از داده‌ها
        """

        processed = []

        for item in items:

            processed_item = self.process(item)
            processed.append(processed_item)

        # حذف داده‌های تکراری بر اساس متن اصلی
        unique = self.deduplicator.remove_duplicates(
            processed
        )

        return unique