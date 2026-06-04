# core/deduplicator.py

import hashlib


class Deduplicator:
    """
    حذف داده‌های تکراری از لیست‌ها
    """

    def __init__(self):

        self.seen_hashes = set()

    def _hash_item(self, item: str) -> str:
        """
        ساخت هش برای هر آیتم
        """

        return hashlib.md5(item.encode("utf-8")).hexdigest()

    def remove_duplicates(self, items: list):
        """
        حذف آیتم‌های تکراری
        """

        unique_items = []

        for item in items:

            item_str = str(item)
            item_hash = self._hash_item(item_str)

            if item_hash not in self.seen_hashes:

                self.seen_hashes.add(item_hash)
                unique_items.append(item)

        return unique_items

    def reset(self):
        """
        پاک کردن حافظه داخلی
        """

        self.seen_hashes = set()