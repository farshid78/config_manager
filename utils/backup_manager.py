import shutil
from datetime import datetime
from pathlib import Path

from config.path_manager import paths


class BackupManager:

    def __init__(self):

        self.db_path = paths.DATABASE_FILE
        self.backup_dir = paths.STORAGE / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self):

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        backup_file = self.backup_dir / f"backup_{now}.db"

        shutil.copy2(self.db_path, backup_file)

        return str(backup_file)