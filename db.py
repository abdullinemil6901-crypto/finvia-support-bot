import sqlite3
from datetime import datetime
import pytz

DB_PATH = "stats.db"
MSK = pytz.timezone("Europe/Moscow")

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
