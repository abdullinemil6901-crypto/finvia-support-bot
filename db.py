"""
db.py — статистика событий (логирование обращений).
Поддерживает SQLite (fallback) и Supabase (если задан DATABASE_URL).
"""
import os
import sqlite3
from datetime import datetime
import pytz

MSK = pytz.timezone("Europe/Moscow")

USE_SUPABASE = bool(os.getenv("SUPABASE_API_KEY") and os.getenv("SUPABASE_PROJECT_REF"))

if USE_SUPABASE:
    from supabase_client import log_event, get_today_stats
else:
    DB_PATH = "stats.db"

    def init_db():
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    user_id INTEGER,
                    username TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def log_event(event_type: str, user_id: int, username: str = None):
        now = datetime.now(MSK).isoformat()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO events (event_type, user_id, username, created_at) VALUES (?, ?, ?, ?)",
                (event_type, user_id, username, now)
            )
            conn.commit()

    def get_today_stats() -> dict:
        today = datetime.now(MSK).strftime("%Y-%m-%d")
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT event_type, COUNT(*) FROM events WHERE created_at LIKE ? GROUP BY event_type",
                (f"{today}%",)
            )
            return dict(cursor.fetchall())