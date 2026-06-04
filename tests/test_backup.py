from utils.backup_manager import BackupManager

backup = BackupManager()

file = backup.create_backup()

print("Backup created:", file)