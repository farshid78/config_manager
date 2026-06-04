# storage/json_manager.py

import json
from pathlib import Path


class JsonManager:

    @staticmethod
    def load(file_path: Path, default=None):

        if default is None:
            default = {}

        if not file_path.exists():
            return default

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)

        except Exception:
            return default

    @staticmethod
    def save(file_path: Path, data):

        file_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )