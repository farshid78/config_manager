# database/database_manager.py

import sqlite3

from config.path_manager import paths


class DatabaseManager:
    """
    مدیر پایگاه داده پروژه
    """

    def __init__(self):

        self.db_path = paths.DATABASE_FILE

        self.initialize()

    def connect(self):

        return sqlite3.connect(self.db_path)

    def initialize(self):

        conn = self.connect()

        # جدول حافظه مشترک
        conn.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        # جدول کاربران
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            joined_at TEXT
        )
        """)

        conn.commit()
        conn.close()

    def set(self, key, value):

        conn = self.connect()

        conn.execute(
            """
            INSERT OR REPLACE INTO memory
            (key, value)
            VALUES (?, ?)
            """,
            (key, value)
        )

        conn.commit()
        conn.close()

    def get(self, key):

        conn = self.connect()

        cursor = conn.execute(
            """
            SELECT value
            FROM memory
            WHERE key = ?
            """,
            (key,)
        )

        row = cursor.fetchone()

        conn.close()

        if row:
            return row[0]

        return None

    def delete(self, key):

        conn = self.connect()

        conn.execute(
            """
            DELETE FROM memory
            WHERE key = ?
            """,
            (key,)
        )

        conn.commit()
        conn.close()

    def add_user(
        self,
        user_id,
        first_name,
        username,
        joined_at
    ):

        conn = self.connect()

        conn.execute(
            """
            INSERT OR IGNORE INTO users
            (
                user_id,
                first_name,
                username,
                joined_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                first_name,
                username,
                joined_at
            )
        )

        conn.commit()
        conn.close()

    def get_users_count(self):

        conn = self.connect()

        cursor = conn.execute(
            """
            SELECT COUNT(*)
            FROM users
            """
        )

        count = cursor.fetchone()[0]

        conn.close()

        return count