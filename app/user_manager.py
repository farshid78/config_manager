# app/user_manager.py

from datetime import datetime

from database.database_manager import DatabaseManager


db = DatabaseManager()


def register_user(user):

    now = datetime.now().isoformat()

    db.add_user(
        user_id=user.id,
        first_name=user.first_name,
        username=user.username,
        joined_at=now
    )

    db.update_user_activity(
        user_id=user.id,
        activity_time=now
    )