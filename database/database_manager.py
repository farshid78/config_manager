from itertools import count
import sqlite3

try:
    from config.path_manager import paths
except Exception:
    try:
        import paths
    except Exception:
        paths = None

class DatabaseManager:

    def __init__(self):
        if paths and hasattr(paths, "DATABASE_FILE"):
            self.db_path = paths.DATABASE_FILE
        else:
            self.db_path = "database.sqlite3"

        self.initialize()

    def connect(self):
        return sqlite3.connect(self.db_path)

# ====================================
# DATABASE INIT
# ====================================

    def initialize(self):

        conn = self.connect()

        conn.execute("""
          CREATE TABLE IF NOT EXISTS memory (
        key TEXT PRIMARY KEY,
        value TEXT
         )
     """)

        conn.execute("""
             CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        joined_at TEXT
    )
    """)
        

        conn.execute("""
                CREATE TABLE IF NOT EXISTS vip_users (
        user_id INTEGER PRIMARY KEY,
        added_at TEXT
        )
        """)  


        conn.execute("""
            CREATE TABLE IF NOT EXISTS clean_ips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT UNIQUE,
            created_at TEXT
             )
        """)
        

        conn.execute("""
    CREATE TABLE IF NOT EXISTS user_stats (
        user_id INTEGER PRIMARY KEY,
        start_count INTEGER DEFAULT 0,
        last_activity TEXT
    )
    """)

        conn.execute("""
    CREATE TABLE IF NOT EXISTS processed_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        input_text TEXT,
        output_text TEXT,
        created_at TEXT,
        country_code TEXT,
        protocol TEXT,
        host TEXT
    )
    """)

        conn.execute("""
    CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        value TEXT,
        created_at TEXT
    )
    """)

        # Migration

        try:
            conn.execute(
                "ALTER TABLE processed_data ADD COLUMN country_code TEXT"
            )
        except:
            pass

        try:
            conn.execute(
                "ALTER TABLE processed_data ADD COLUMN protocol TEXT"
            )
        except:
            pass

        try:
            conn.execute(
                "ALTER TABLE processed_data ADD COLUMN host TEXT"
            )
        except:
            pass

        # Indexes

        conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_country
    ON processed_data(country_code)
    """)

        conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_protocol
    ON processed_data(protocol)
    """)

        conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_created
    ON processed_data(created_at)
    """)

        conn.commit()
        conn.close()

    # ====================================
    # CONFIG STORAGE
    # ====================================

    def save_processed_data(
        self,
        input_text,
        output_text,
        created_at,
        country_code=None,
        protocol=None,
        host=None
    ):

        conn = self.connect()

        conn.execute("""
        INSERT INTO processed_data (
            input_text,
            output_text,
            created_at,
            country_code,
            protocol,
            host
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            input_text,
            output_text,
            created_at,
            country_code,
            protocol,
            host
        ))

        conn.commit()
        conn.close()

    def get_last_processed(self, limit=10):

            conn = self.connect()

            cursor = conn.execute("""
             SELECT
                  input_text,
                 country_code,
                 protocol,
                  host,
                  created_at
             FROM processed_data
             ORDER BY id DESC
             LIMIT ?
             """, (limit,))

            rows = cursor.fetchall()

            conn.close()

            return rows

    # ====================================
    # FILTERS
    # ====================================

    def get_by_country(
        self,
        country_code,
        limit=100
    ):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT *
        FROM processed_data
        WHERE country_code = ?
        ORDER BY id DESC
        LIMIT ?
        """, (
            country_code.upper(),
            limit
        ))

        rows = cursor.fetchall()

        conn.close()

        return rows

    def get_by_protocol(
        self,
        protocol,
        limit=100
    ):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT *
        FROM processed_data
        WHERE protocol = ?
        ORDER BY id DESC
        LIMIT ?
        """, (
            protocol.lower(),
            limit
        ))

        rows = cursor.fetchall()

        conn.close()

        return rows

    def get_by_country_protocol(
        self,
        country_code,
        protocol,
        limit=100
    ):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT *
        FROM processed_data
        WHERE country_code = ?
        AND protocol = ?
        ORDER BY id DESC
        LIMIT ?
        """, (
            country_code.upper(),
            protocol.lower(),
            limit
        ))

        rows = cursor.fetchall()

        conn.close()

        return rows

    # ====================================
    # CACHE
    # ====================================

    def set_cache(self, key, value, created_at):

        conn = self.connect()

        conn.execute("""
        INSERT OR REPLACE INTO cache
        (key, value, created_at)
        VALUES (?, ?, ?)
        """, (
            key,
            value,
            created_at
        ))

        conn.commit()
        conn.close()

    def get_cache(self, key):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT value
        FROM cache
        WHERE key = ?
        """, (key,))

        row = cursor.fetchone()

        conn.close()

        return row[0] if row else None

    # ====================================
    # USERS
    # ====================================

    def add_user(self, user_id, first_name, username, joined_at):

        conn = self.connect()

        conn.execute("""
        INSERT OR IGNORE INTO users
        (
            user_id,
            first_name,
            username,
            joined_at
        )
        VALUES (?, ?, ?, ?)
        """, (
            user_id,
            first_name,
            username,
            joined_at
        ))

        conn.commit()
        conn.close()

    def get_all_users(self):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT user_id
        FROM users
        """)

        rows = cursor.fetchall()

        conn.close()

        return rows

    def get_users_count(self):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT COUNT(*)
        FROM users
        """)

        count = cursor.fetchone()[0]

        conn.close()

        return count
        # ====================================
    # USER STATS
    # ====================================

    def update_user_activity(
        self,
        user_id,
        activity_time
    ):

        conn = self.connect()

        conn.execute("""
        INSERT OR IGNORE INTO user_stats
        (
            user_id,
            start_count,
            last_activity
        )
        VALUES (?, 0, ?)
        """, (
            user_id,
            activity_time
        ))

        conn.execute("""
        UPDATE user_stats
        SET
            start_count = start_count + 1,
            last_activity = ?
        WHERE user_id = ?
        """, (
            activity_time,
            user_id
        ))

        conn.commit()
        conn.close()

    def get_total_starts(self):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT COALESCE(
            SUM(start_count),
            0
        )
        FROM user_stats
        """)

        total = cursor.fetchone()[0]

        conn.close()

        return total
    
    def add_vip_user(self, user_id, added_at):

        conn = self.connect()

        conn.execute("""
        INSERT OR REPLACE INTO vip_users
        (
            user_id,
            added_at
        )
        VALUES (?, ?)
        """, (
            user_id,
            added_at
        ))

        conn.commit()
        conn.close()

    def remove_vip_user(self, user_id):

        conn = self.connect()

        cursor = conn.execute("""
        DELETE FROM vip_users
        WHERE user_id = ?
        """, (user_id,))

        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        return deleted > 0

    def is_vip(self, user_id):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT user_id
        FROM vip_users
        WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()

        conn.close()

        return row is not None

    def get_all_vips(self):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT
             user_id,
             added_at
        FROM vip_users
        ORDER BY added_at DESC
        """)

        rows = cursor.fetchall()

        conn.close()

        return rows
    def get_vip_count(self):

        conn = self.connect()

        cursor = conn.execute("""
            SELECT COUNT(*)
            FROM vip_users
            """)

        count = cursor.fetchone()[0]

        conn.close()

        return count

    def get_vip_users(self):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT user_id
        FROM vip_users
        """)

        rows = cursor.fetchall()

        conn.close()

        return rows

    def vip_exists(self, user_id):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT user_id
        FROM vip_users
        WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()

        conn.close()

        return row is not None

    def get_vip_info(self, user_id):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT
            user_id,
            added_at
        FROM vip_users
        WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()

        conn.close()

        return row


    # ====================================
    # MEMORY
    # ====================================

    def set(self, key, value):

        conn = self.connect()

        conn.execute("""
        INSERT OR REPLACE INTO memory
        (
            key,
            value
        )
        VALUES (?, ?)
        """, (
            key,
            value
        ))

        conn.commit()
        conn.close()

    def get(self, key):

        conn = self.connect()

        cursor = conn.execute("""
        SELECT value
        FROM memory
        WHERE key = ?
        """, (key,))

        row = cursor.fetchone()

        conn.close()

        return row[0] if row else None

    def delete(self, key):

        conn = self.connect()

        conn.execute("""
        DELETE FROM memory
        WHERE key = ?
        """, (key,))

        conn.commit()
        conn.close()
# ====================================
# CLEAN IPS
# ====================================

def add_clean_ip(self, ip, created_at):

    conn = self.connect()

    conn.execute("""
    INSERT OR IGNORE INTO clean_ips
    (
        ip,
        created_at
    )
    VALUES (?, ?)
    """, (
        ip,
        created_at
    ))

    conn.commit()
    conn.close()


def get_clean_ips(self):

    conn = self.connect()

    cursor = conn.execute("""
    SELECT ip
    FROM clean_ips
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]


def get_clean_ip_count(self):

    conn = self.connect()

    cursor = conn.execute("""
    SELECT COUNT(*)
    FROM clean_ips
    """)

    count = cursor.fetchone()[0]

    conn.close()

    return count


def delete_old_clean_ips(self, days=5):

    conn = self.connect()

    conn.execute(f"""
    DELETE FROM clean_ips
    WHERE datetime(created_at)
    <
    datetime('now','-{days} day')
    """)

    conn.commit()
    conn.close()