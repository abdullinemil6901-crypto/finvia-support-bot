"""
Support Bot — REST API v2
Эндпоинты для админ-дашборда.
Масштабируемая архитектура для 20+ команд.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from functools import lru_cache
import os
import time
import database
import schedule_manager

# Простое кэширование в памяти
_summary_cache = {"data": None, "timestamp": 0}
CACHE_TTL = 30  # секунды

app = FastAPI(
    title="Support Bot API",
    description="API для админ-дашборда Support Bot",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount dashboard static files
dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")


# ─────────────────────────────────────────────
# КОНФИГУРАЦИЯ КОМАНД — масштабируемость
# ─────────────────────────────────────────────

# Все команды/категории в одном месте — легко добавить 20+ команд
COMMANDS_CONFIG = {
    "apply_cancel_payout":       {"label": "🚫 Отмена выплаты",                "needs_order_id": True},
    "apply_payout_not_visible":  {"label": "👁 Выплата не видна на токене",    "needs_order_id": True},
    "apply_extend_time":         {"label": "⏱ Продлить время ордера",          "needs_order_id": True},
    "apply_no_receipt":          {"label": "🧾 Нет чека / не прогрузился",     "needs_order_id": True},
    "apply_wrong_receipt":       {"label": "📎 Неверный чек прикреплён",       "needs_order_id": True},
    "apply_wrong_cvu":           {"label": "❌ Неверный CVU / не наш реквизит", "needs_order_id": True},
    "apply_wrong_requisite":     {"label": "🚷 Не наш реквизит",               "needs_order_id": True},
    "apply_verify_requisites":   {"label": "⚙️ Верификация реквизитов",         "needs_order_id": True},
    "apply_tech_issue":          {"label": "⚙️ Технический сбой",              "needs_order_id": True},
    "apply_token_issue":         {"label": "🔧 Токен не работает",             "needs_order_id": False},
    "apply_appeal":              {"label": "⚖️ Апелляция",                     "needs_order_id": True},
    "apply_no_traffic":          {"label": "📡 Нет трафика / ордеров",         "needs_order_id": False},
    "apply_increase_limits":     {"label": "📈 Увеличить лимиты",              "needs_order_id": True},
}


# ─────────────────────────────────────────────
# Pydantic модели
# ─────────────────────────────────────────────

class TicketResponse(BaseModel):
    id: int
    trader_id: int
    trader_username: Optional[str] = ""
    trader_name: Optional[str] = ""
    label: Optional[str] = ""
    order_id: Optional[str] = None
    status: str
    taken_by: Optional[str] = None
    taken_at: Optional[str] = None
    closed_at: Optional[str] = None
    created_at: str
    trader_chat_id: Optional[int] = None


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class SupportStats(BaseModel):
    username: str
    total: int
    closed: int
    in_progress: int
    avg_seconds: Optional[float]


class CommandInfo(BaseModel):
    key: str
    label: str
    needs_order_id: bool
    ticket_count: int


class DutyResponse(BaseModel):
    support_username: Optional[str]
    shift: Optional[str]


class SetDutyRequest(BaseModel):
    support_username: str
    shift: Optional[str] = None


# ─────────────────────────────────────────────
# Эндпоинты — Тикеты (с пагинацией и фильтрами)
# ─────────────────────────────────────────────

@app.get("/api/tickets", response_model=TicketListResponse)
def get_tickets(
    status: Optional[str] = Query(None, description="Фильтр по статусу: open, in_progress, closed"),
    support: Optional[str] = Query(None, description="Фильтр по саппорту (username)"),
    label: Optional[str] = Query(None, description="Фильтр по категории (label)"),
    trader_id: Optional[int] = Query(None, description="Фильтр по ID трейдера"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=500, description="Тикетов на странице"),
):
    """
    Получить тикеты с пагинацией и фильтрами.
    - /api/tickets — все тикеты (пагинация)
    - /api/tickets?status=open — только открытые
    - /api/tickets?support=username — тикеты саппорта
    - /api/tickets?label=xxx — по категории
    - /api/tickets?trader_id=123 — по трейдеру
    """
    offset = (page - 1) * per_page
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if support:
        conditions.append("taken_by = ?")
        params.append(support)
    if label:
        conditions.append("label = ?")
        params.append(label)
    if trader_id:
        conditions.append("trader_id = ?")
        params.append(trader_id)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    with database.get_connection() as conn:
        # Получаем общее количество
        total = conn.execute(
            f"SELECT COUNT(*) FROM tickets WHERE {where_clause}",
            params
        ).fetchone()[0]

        # Получаем тикеты для текущей страницы
        rows = conn.execute(
            f"SELECT * FROM tickets WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset]
        ).fetchall()

    tickets = [_row_to_ticket_full(row) for row in rows]
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return TicketListResponse(
        tickets=tickets,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@app.get("/api/tickets/open", response_model=list[TicketResponse])
def get_open_tickets():
    """Получить все открытые тикеты (для саппортов)."""
    rows = database.get_open_tickets()
    return [_row_to_ticket(row) for row in rows]


@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int):
    """Получить один тикет по ID."""
    row = database.get_ticket(ticket_id)
    if not row:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    return _row_to_ticket_full(row)


# ─────────────────────────────────────────────
# Эндпоинты — Статистика
# ─────────────────────────────────────────────

@app.get("/api/supports")
def get_supports():
    """Получить список всех саппортов."""
    with database.get_connection() as conn:
        rows = conn.execute("""
            SELECT DISTINCT taken_by FROM tickets
            WHERE taken_by IS NOT NULL AND taken_by != ''
            ORDER BY taken_by
        """).fetchall()
        return [{"username": row[0]} for row in rows]


@app.get("/api/stats", response_model=list[SupportStats])
def get_stats():
    """Статистика по всем саппортам."""
    with database.get_connection() as conn:
        rows = conn.execute("""
            SELECT
                taken_by as username,
                COUNT(*) as total,
                SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) as in_progress,
                AVG(
                    CASE
                        WHEN status='closed' AND taken_at IS NOT NULL AND closed_at IS NOT NULL
                        THEN (julianday(closed_at) - julianday(taken_at)) * 86400
                        ELSE NULL
                    END
                ) as avg_seconds
            FROM tickets
            WHERE taken_by IS NOT NULL
            GROUP BY taken_by
            ORDER BY total DESC
        """).fetchall()
        return [
            SupportStats(
                username=row[0] or "unknown",
                total=row[1] or 0,
                closed=row[2] or 0,
                in_progress=row[3] or 0,
                avg_seconds=row[4]
            )
            for row in rows
        ]


@app.get("/api/stats/{username}", response_model=SupportStats)
def get_support_stats(username: str):
    """Личная статистика конкретного саппорта."""
    stats = database.get_support_personal_stats(username)
    return SupportStats(
        username=username,
        total=stats["total"],
        closed=stats["closed"],
        in_progress=stats["in_progress"],
        avg_seconds=stats["avg_seconds"]
    )


# ─────────────────────────────────────────────
# Эндпоинты — Команды (для дашборда)
# ─────────────────────────────────────────────

@app.get("/api/commands", response_model=list[CommandInfo])
def get_commands():
    """Список всех доступных команд с количеством тикетов."""
    with database.get_connection() as conn:
        # Получаем количество тикетов по каждой категории
        counts = conn.execute("""
            SELECT label, COUNT(*) as cnt
            FROM tickets
            GROUP BY label
        """).fetchall()
        count_map = {row[0]: row[1] for row in counts}

    result = []
    for key, config in COMMANDS_CONFIG.items():
        result.append(CommandInfo(
            key=key,
            label=config["label"],
            needs_order_id=config["needs_order_id"],
            ticket_count=count_map.get(config["label"], 0)
        ))

    # Сортируем по количеству тикетов (популярные первые)
    result.sort(key=lambda x: x.ticket_count, reverse=True)
    return result


# ─────────────────────────────────────────────
# Эндпоинты — Дежурство
# ─────────────────────────────────────────────

@app.get("/api/duty", response_model=DutyResponse)
def get_duty():
    """Получить текущего дежурного (день/ночь)."""
    duty_info = schedule_manager.get_duty_info()
    return DutyResponse(
        support_username=", ".join(duty_info["names"]) if duty_info["names"] else None,
        shift=duty_info["shift"]
    )


@app.get("/api/schedule")
def get_schedule():
    """Получить расписание на текущую неделю."""
    week = schedule_manager.get_week_schedule()
    return {
        "week": week,
        "today": datetime.now().strftime("%Y-%m-%d"),
    }


@app.post("/api/duty")
def set_duty(req: SetDutyRequest):
    """Назначить дежурного на смену."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    shift = req.shift or ("day" if 9 <= now.hour < 21 else "night")
    schedule_manager.set_duty(date_str, shift, [req.support_username])
    return {"success": True, "support_username": req.support_username, "shift": shift}


# ─────────────────────────────────────────────
# Эндпоинты — Сводка (для главной дашборда)
# ─────────────────────────────────────────────

@app.get("/api/summary")
def get_summary():
    """Сводка для главной страницы дашборда. Кэшируется на 30 сек."""
    global _summary_cache

    # Проверяем кэш
    now = time.time()
    if _summary_cache["data"] and (now - _summary_cache["timestamp"]) < CACHE_TTL:
        return _summary_cache["data"]

    with database.get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        open_count = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
        in_progress = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'").fetchone()[0]
        closed = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='closed'").fetchone()[0]

        # Тикеты по категориям
        by_label = conn.execute("""
            SELECT label, COUNT(*) as cnt
            FROM tickets
            GROUP BY label
            ORDER BY cnt DESC
        """).fetchall()

        # Тикеты по часам (последние 24 часа)
        by_hour = conn.execute("""
            SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt
            FROM tickets
            WHERE created_at >= datetime('now', '-1 day')
            GROUP BY hour
            ORDER BY hour
        """).fetchall()

        # Тикеты по дням (последние 7 дней)
        by_day = conn.execute("""
            SELECT strftime('%Y-%m-%d', created_at) as day, COUNT(*) as cnt
            FROM tickets
            WHERE created_at >= datetime('now', '-7 days')
            GROUP BY day
            ORDER BY day
        """).fetchall()

    duty = schedule_manager.get_current_duty()

    result = {
        "total": total,
        "open": open_count,
        "in_progress": in_progress,
        "closed": closed,
        "by_label": [{"label": row[0], "count": row[1]} for row in by_label],
        "by_hour": [{"hour": row[0], "count": row[1]} for row in by_hour],
        "by_day": [{"day": row[0], "count": row[1]} for row in by_day],
        "current_duty": ", ".join(duty) if duty else None
    }

    # Сохраняем в кэш
    _summary_cache = {"data": result, "timestamp": now}
    return result


# ─────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────

def _row_to_ticket(row, is_open: bool = False) -> TicketResponse:
    """Конвертирует row из get_open_tickets() в TicketResponse."""
    return TicketResponse(
        id=row[0],
        trader_id=row[1],
        trader_username=row[2] or "",
        trader_name=row[3] or "",
        label=row[4],
        order_id=row[5],
        status="open",
        taken_by=None,
        taken_at=None,
        closed_at=None,
        created_at=row[6],
        trader_chat_id=row[7] if len(row) > 7 else None
    )


def _row_to_ticket_full(row) -> TicketResponse:
    """Конвертирует row из SELECT * в TicketResponse."""
    return TicketResponse(
        id=row[0],
        trader_id=row[1],
        trader_username=row[2] or "",
        trader_name=row[3] or "",
        label=row[4] or "",
        order_id=row[5],
        status=row[6],
        taken_by=row[7],
        taken_at=row[9] if len(row) > 9 else None,
        closed_at=row[10] if len(row) > 10 else None,
        created_at=row[11] if len(row) > 11 else "",
        trader_chat_id=row[12] if len(row) > 12 else None
    )


# ─────────────────────────────────────────────
# Эндпоинты — Мониторинг
# ─────────────────────────────────────────────

@app.get("/health")
def health_check():
    """Healthcheck для uptime-мониторинга."""
    try:
        # Проверяем подключение к БД
        with database.get_connection() as conn:
            conn.execute("SELECT 1")
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/stats_summary")
def get_stats_summary():
    """Быстрая сводка для мониторинга."""
    try:
        with database.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            open_count = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
            closed = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='closed'").fetchone()[0]
            in_progress = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'").fetchone()[0]

        return {
            "total": total,
            "open": open_count,
            "in_progress": in_progress,
            "closed": closed,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Запуск
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
