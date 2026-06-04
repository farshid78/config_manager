import json
import csv
from pathlib import Path

from database.database_manager import DatabaseManager
from config.path_manager import BASE_DIR


db = DatabaseManager()


class ExportManager:

    def __init__(self):

        self.export_dir = BASE_DIR / "exports"
        self.export_dir.mkdir(exist_ok=True)
    # --------------------
    # EXPORT USERS
    # --------------------
    def export_users_json(self):

        users = db.get_all_users()

        data = [
            {"user_id": u[0]}
            for u in users
        ]

        file_path = self.export_dir / "users.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return file_path

    def export_users_csv(self):

        users = db.get_all_users()

        file_path = self.export_dir / "users.csv"

        with open(file_path, "w", newline="", encoding="utf-8") as f:

            writer = csv.writer(f)
            writer.writerow(["user_id"])

            for u in users:
                writer.writerow([u[0]])

        return file_path

    # --------------------
    # EXPORT HISTORY
    # --------------------
    def export_history_json(self):

        rows = db.get_last_processed(100)

        data = [
            {
                "input": r[0],
                "output": r[1],
                "created_at": r[2]
            }
            for r in rows
        ]

        file_path = self.export_dir / "history.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return file_path