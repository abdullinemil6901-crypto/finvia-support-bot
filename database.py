"""
database.py — работа с тикетами и саппортами.
Поддерживает SQLite (fallback) и Supabase (если задан API_KEY и PROJECT_REF).

Примечание: все функции определены на верхнем уровне модуля,
внутри происходит выбор между SQLite и Supabase.
"""
import os
import sqlite3
from datetime import datetime
from typing import Optional

# Определяем какой backend используем
USE_SUPABASE = bool(os.getenv("SUPABASE_API_KEY") and os.getenv("SUPABASE_PROJECT_REF"))
DB_PATH = os.path.join(os.path.dirname(__file__), "support_bot.db")


def get_connection():
    """Получить соединение с SQLite. Используется только если USE_SUPABASE=False."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Инициализировать SQLite БД. Supabase инициализируется через миграции."""
    if USE_SUPABASE:
        return  # Ничего не делаем для Supabase

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


def save_ticket(trader_id: int, trader_username: str, trader_name: str, label: str,
                order_id: str = None, trader_chat_id: int = None, team_name: str = None) -> int:
    """Сохранить тикет."""
    if USE_SUPABASE:
        from supabase_client import save_ticket as sb_save
        return sb_save(trader_id, trader_username, trader_name, label, order_id, trader_chat_id, team_name)

    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO tickets (trader_id, trader_username, trader_name, label, order_id, created_at, trader_chat_id, team_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (trader_id, trader_username or "", trader_name or "", label, order_id,
             datetime.now().isoformat(), trader_chat_id, team_name)
        )
        conn.commit()
        return cursor.lastrowid


def take_ticket(ticket_id: int, support_username: str, support_id: int):
    """Взять тикет в работу."""
    if USE_SUPABASE:
        from supabase_client import take_ticket as sb_take
        return sb_take(ticket_id, support_username, support_id)

    with get_connection() as conn:
        conn.execute(
            """UPDATE tickets SET status='in_progress', taken_by=?, taken_by_id=?, taken_at=? WHERE id=?""",
            (support_username, support_id, datetime.now().isoformat(), ticket_id)
        )
        conn.commit()


def close_ticket(ticket_id: int):
    """Закрыть тикет."""
    if USE_SUPABASE:
        from supabase_client import close_ticket as sb_close
        return sb_close(ticket_id)

    with get_connection() as conn:
        conn.execute(
            """UPDATE tickets SET status='closed', closed_at=? WHERE id=?""",
            (datetime.now().isoformat(), ticket_id)
        )
        conn.commit()


def get_ticket(ticket_id: int):
    """Получить тикет по ID."""
    if USE_SUPABASE:
        from supabase_client import get_ticket as sb_get
        return sb_get(ticket_id)

    with get_connection() as conn:
        return conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()


def get_support_stats(support_username: str):
    """Статистика саппорта."""
    if USE_SUPABASE:
        from supabase_client import get_support_personal_stats as sb_stats
        return sb_stats(support_username)

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
    """Статистика по часам."""
    if USE_SUPABASE:
        from supabase_client import get_hourly_stats as sb_stats
        return sb_stats()

    with get_connection() as conn:
        rows = conn.execute(
            """SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt
               FROM tickets GROUP BY hour ORDER BY hour"""
        ).fetchall()
        return rows


def get_label_stats():
    """Статистика по категориям."""
    if USE_SUPABASE:
        from supabase_client import get_label_stats as sb_stats
        return sb_stats()

    with get_connection() as conn:
        rows = conn.execute(
            """SELECT label, COUNT(*) as cnt FROM tickets GROUP BY label ORDER BY cnt DESC"""
        ).fetchall()
        return rows


def add_support(tg_id: int, username: str, full_name: str):
    """Добавить саппорта."""
    if USE_SUPABASE:
        from supabase_client import add_support as sb_add
        return sb_add(tg_id, username, full_name)

    with get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO supports (tg_id, username, full_name, added_at)
               VALUES (?, ?, ?, ?)""",
            (tg_id, username, full_name, datetime.now().isoformat())
        )
        conn.commit()


def get_all_supports():
    """Получить всех саппортов."""
    if USE_SUPABASE:
        from supabase_client import get_all_supports as sb_get
        return sb_get()

    with get_connection() as conn:
        return conn.execute("SELECT * FROM supports").fetchall()


def get_trader_tickets(trader_id: int):
    """Получить тикеты трейдера."""
    if USE_SUPABASE:
        from supabase_client import get_trader_tickets as sb_get
        return sb_get(trader_id)

    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, label, order_id, status, taken_by, created_at, closed_at
               FROM tickets WHERE trader_id=? ORDER BY created_at DESC""",
            (trader_id,)
        ).fetchall()
        return rows


def get_support_personal_stats(support_username: str):
    """Личная статистика саппорта."""
    if USE_SUPABASE:
        from supabase_client import get_support_personal_stats as sb_stats
        return sb_stats(support_username)

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
    """Получить открытые тикеты."""
    if USE_SUPABASE:
        from supabase_client import get_open_tickets as sb_get
        return sb_get()

    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, trader_id, trader_username, trader_name, label, order_id, created_at, trader_chat_id
               FROM tickets WHERE status='open' ORDER BY created_at ASC"""
        ).fetchall()
        return rows


def get_tickets_by_support(support_username: str):
    """Получить тикеты саппорта."""
    if USE_SUPABASE:
        from supabase_client import get_tickets_by_support as sb_get
        return sb_get(support_username)

    with get_connection() as conn:
        rows = conn.execute(
            """SELECT id, label, order_id, status, trader_username, trader_name, taken_at, closed_at, created_at
               FROM tickets WHERE taken_by=? ORDER BY created_at DESC""",
            (support_username,)
        ).fetchall()
        return rows


def remove_support(tg_id: int):
    """Удалить саппорта."""
    if USE_SUPABASE:
        from supabase_client import remove_support as sb_remove
        return sb_remove(tg_id)

    with get_connection() as conn:
        conn.execute("DELETE FROM supports WHERE tg_id=?", (tg_id,))
        conn.commit()


def get_support_by_tg_id(tg_id: int):
    """Найти саппорта по TG ID."""
    if USE_SUPABASE:
        from supabase_client import get_support_by_tg_id as sb_get
        return sb_get(tg_id)

    with get_connection() as conn:
        return conn.execute("SELECT * FROM supports WHERE tg_id=?", (tg_id,)).fetchone()


def get_all_tickets():
    """Получить все тикеты."""
    if USE_SUPABASE:
        from supabase_client import get_all_tickets as sb_get
        return sb_get()

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, trader_id, trader_username, trader_name, label, order_id,
                   status, taken_by, taken_at, closed_at, created_at
            FROM tickets ORDER BY created_at DESC
        """).fetchall()
        return rows


def get_tickets_summary():
    """Сводка по тикетам."""
    if USE_SUPABASE:
        from supabase_client import get_tickets_summary as sb_summary
        return sb_summary()

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


def get_support_stats_all():
    """Статистика по всем саппортам."""
    if USE_SUPABASE:
        from supabase_client import get_support_stats as sb_stats
        return sb_stats()

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
