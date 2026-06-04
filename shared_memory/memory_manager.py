from database.database_manager import DatabaseManager


class SharedMemory:

    def __init__(self):

        self.db = DatabaseManager()

    def set(self, key, value):

        self.db.set(key, value)

    def get(self, key):

        return self.db.get(key)

    def delete(self, key):

        self.db.delete(key)