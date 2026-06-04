from database.database_manager import DatabaseManager


class QueryService:

    def __init__(self):
        self.db = DatabaseManager()

    # ---------------------------
    # last N configs
    # ---------------------------
    def get_last(self, limit: int):

        conn = self.db.connect()

        cursor = conn.execute("""
            SELECT input_text, output_text, created_at
            FROM processed_data
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return rows

    # ---------------------------
    # by country
    # ---------------------------
    def get_by_country(self, country_code, limit=100):

        conn = self.db.connect()

        cursor = conn.execute("""
            SELECT input_text, output_text, created_at, country_code, protocol, host
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