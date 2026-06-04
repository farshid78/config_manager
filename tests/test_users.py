# tests/test_users.py

import sqlite3

from config.path_manager import paths


conn = sqlite3.connect(
    paths.DATABASE_FILE
)

cursor = conn.execute(
    """
    SELECT
        user_id,
        first_name,
        username,
        joined_at
    FROM users
    """
)

rows = cursor.fetchall()

print("\n=== USERS ===\n")

for row in rows:
    print(row)

print("\nTotal Users:", len(rows))

conn.close()