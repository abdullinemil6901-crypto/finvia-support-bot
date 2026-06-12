"""
database.py — работа с тикетами и саппортами.
Поддерживает SQLite (fallback) и Supabase (если задан DATABASE_URL).
"""
import os
import sqlite3
from datetime import datetime
from typing import Optional

# Если есть DATABASE_URL — используем Supabase
USE_SUPABASE = bool(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_API_KEY") or os.getenv("SUPABASE_PROJECT_REF"))

if USE_SUPABASE:
    from supabase_client import (
        save_ticket, take_ticket, close_ticket, get_ticket,
        get_open_tickets, get_all_tickets, get_tickets_by_support,
        get_trader_tickets, get_support_personal_stats, get_label_stats,
        get_hourly_stats, add_support, get_all_supports, get_support_by_tg_id,
        remove_support, get_tickets_summary, get_support_stats
    )

    def init_db():
        """Supabase инициализируется через миграции — ничего делать не нужно."""
        pass

    def get_connection():
        return None
else:
    # ============================================
    # SQLite реализация (fallback)
    # ============================================
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_taken_by ON tickets(taken_by)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_label ON tickets(label)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status_created ON tickets(status, created_at DESC)")
            try:
                conn.execute("ALTER TABLE tickets ADD COLUMN trader_chat_id INTEGER")
            except Exception:
                pass
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

    def save_ticket(trader_id: int, trader_username: str, trader_name: str, label: str, order_id: str = None, trader_chat_id: int = None) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO tickets (trader_id, trader_username, trader_name, label, order_id, created_at, trader_chat_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (trader_id, trader_username or "", trader_name or "", label, order_id, datetime.now().isoformat(), trader_chat_id)
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
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt
                   FROM tickets GROUP BY hour ORDER BY hour"""
            ).fetchall()
            return rows

    def get_label_stats():
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
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT id, label, order_id, status, taken_by, created_at, closed_at
                   FROM tickets WHERE trader_id=? ORDER BY created_at DESC""",
                (trader_id,)
            ).fetchall()
            return rows

    def get_support_personal_stats(support_username: str):
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
            return {"total": total, "closed": closed, "in_progress": in_progress, "avg_seconds": avg_time}

    def get_open_tickets():
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT id, trader_id, trader_username, trader_name, label, order_id, created_at, trader_chat_id
                   FROM tickets WHERE status='open' ORDER BY created_at ASC"""
            ).fetchall()
            return rows

    def get_tickets_by_support(support_username: str):
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT id, label, order_id, status, trader_username, trader_name, taken_at, closed_at, created_at
                   FROM tickets WHERE taken_by=? ORDER BY created_at DESC""",
                (support_username,)
            ).fetchall()
            return rows

    def remove_support(tg_id: int):
        with get_connection() as conn:
            conn.execute("DELETE FROM supports WHERE tg_id=?", (tg_id,))
            conn.commit()

    def get_support_by_tg_id(tg_id: int):
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM supports WHERE tg_id=?", (tg_id,)).fetchone()
            return row

    def get_all_tickets():
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT id, trader_id, trader_username, trader_name, label, order_id,
                       status, taken_by, taken_at, closed_at, created_at
                FROM tickets ORDER BY created_at DESC
            """).fetchall()
            return rows

    def get_tickets_summary():
        with get_connection() as conn:
            row = conn.execute(
                """SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'open') as open,
                    COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                    COUNT(*) FILTER (WHERE status = 'closed') as closed,
                    COUNT(*) FILTER (WHERE DATE(created_at) = DATE('now')) as today
                   FROM tickets"""
            ).fetchone()
            return dict(row) if row else {"total": 0, "open": 0, "in_progress": 0, "closed": 0, "today": 0}

    def get_support_stats():
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT taken_by as username,
                          COUNT(*) as total,
                          COUNT(*) FILTER (WHERE status = 'closed') as closed,
                          AVG(
                              CASE
                                  WHEN status = 'closed' AND taken_at IS NOT NULL AND closed_at IS NOT NULL
                                  THEN (julianday(closed_at) - julianday(taken_at)) * 86400
                              END
                          ) as avg_seconds
                   FROM tickets
                   WHERE taken_by IS NOT NULL
                   GROUP BY taken_by
                   ORDER BY total DESC"""
            ).fetchall()
            return [dict(row) for row in rows]