import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "support_bot.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trader_id INTEGER NOT NULL,
                trader_username TEXT,
                trader_name TEXT,
                label TEXT NOT NULL,
                order_id TEXT,
                status TEXT DEFAULT 'open',
                taken_by TEXT,
                taken_by_id INTEGER,
                taken_at TEXT,
                closed_at TEXT,
                created_at TEXT NOT NULL,
                trader_chat_id INTEGER
            )
        """)
        # Миграция: добавить колонку trader_chat_id если её нет
        try:
            conn.execute("ALTER TABLE tickets ADD COLUMN trader_chat_id INTEGER")
            conn.commit()
        except Exception:
            pass  # Колонка уже существует
        conn.execute("""
            CREATE TABLE IF NOT EXISTS supports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                added_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                support_id INTEGER NOT NULL,
                day_of_week INTEGER NOT NULL,
                hour_start INTEGER NOT NULL,
                hour_end INTEGER NOT NULL,
                FOREIGN KEY (support_id) REFERENCES supports(id)
            )
        """)
        conn.commit()


def save_ticket(trader_id: int, trader_username: str, trader_name: str, label: str, order_id: str = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO tickets (trader_id, trader_username, trader_name, label, order_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (trader_id, trader_username or "", trader_name or "", label, order_id, datetime.now().isoformat())
        )
        conn.commit()
        return cursor.lastrowid


def take_ticket(ticket_id: int, support_username: str, support_id: int):
    with get_connection() as conn:
        conn.execute(
            """UPDATE tickets SET status='in_progress', taken_by=?, taken_by_id=?, taken_at=? WHERE id=?""",
            (support_username, support_id, datetime.now().isoformat(), ticket_id)
        )
        conn.commit()


def close_ticket(ticket_id: int):
    with get_connection() as conn:
        conn.execute(
            """UPDATE tickets SET status='closed', closed_at=? WHERE id=?""",
            (datetime.now().isoformat(), ticket_id)
        )
        conn.commit()


def get_ticket(ticket_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        return row


def get_support_stats(support_username: str):
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE taken_by=?", (support_username,)
        ).fetchone()[0]
        closed = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE taken_by=? AND status='closed'", (support_username,)
        ).fetchone()[0]
        avg_time = conn.execute(
            """SELECT AVG((julianday(closed_at) - julianday(taken_at)) * 86400)
               FROM tickets WHERE taken_by=? AND status='closed' AND taken_at IS NOT NULL AND closed_at IS NOT NULL""",
            (support_username,)
        ).fetchone()[0]
        return {"total": total, "closed": closed, "avg_seconds": avg_time}


def get_hourly_stats():
    """Статистика запросов по часам — для анализа просадок трафика."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt
               FROM tickets GROUP BY hour ORDER BY hour"""
        ).fetchall()
        return rows


def get_label_stats():
    """Статистика по типам обращений."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT label, COUNT(*) as cnt FROM tickets GROUP BY label ORDER BY cnt DESC"""
        ).fetchall()
        return rows


def add_support(tg_id: int, username: str, full_name: str):
    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO supports (tg_id, username, full_name, added_at)
               VALUES (?, ?, ?, ?)""",
            (tg_id, username, full_name, datetime.now().isoformat())
        )
        conn.commit()


def get_all_supports():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM supports").fetchall()


def get_trader_tickets(trader_id: int):
    """Возвращает все тикеты трейдера."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, label, order_id, status, taken_by, created_at, closed_at
               FROM tickets WHERE trader_id=? ORDER BY created_at DESC""",
            (trader_id,)
        ).fetchall()
        return rows


def get_support_personal_stats(support_username: str):
    """Персональная статистика саппорта."""
    with get_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE taken_by=?", (support_username,)
        ).fetchone()[0]
        closed = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE taken_by=? AND status='closed'", (support_username,)
        ).fetchone()[0]
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE taken_by=? AND status='in_progress'", (support_username,)
        ).fetchone()[0]
        avg_time = conn.execute(
            """SELECT AVG((julianday(closed_at) - julianday(taken_at)) * 86400)
               FROM tickets WHERE taken_by=? AND status='closed'
               AND taken_at IS NOT NULL AND closed_at IS NOT NULL""",
            (support_username,)
        ).fetchone()[0]
        return {
            "total": total,
            "closed": closed,
            "in_progress": in_progress,
            "avg_seconds": avg_time
        }
