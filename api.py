"""
Support Bot — REST API v2
Эндпоинты для админ-дашборда.
Работает с SQLite (fallback) и Supabase.
"""
import os

# Определяем backend
USE_SUPABASE = bool(os.getenv("SUPABASE_API_KEY") and os.getenv("SUPABASE_PROJECT_REF"))

# Авторизация
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "dev-only-key")

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

from fastapi import FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import time
import pytz
import requests
import schedule_manager
import database


def send_telegram_message(chat_id: int, text: str, parse_mode: str = "HTML"):
    """Отправляет сообщение в Telegram."""
    if not BOT_TOKEN:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }, timeout=10)
        return response.ok
    except Exception:
        return False


def verify_api_key(authorization: Optional[str] = Header(None)):
    """Проверяет API key из заголовка Authorization: Bearer <key>"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format. Use: Bearer <key>")

    token = authorization.replace("Bearer ", "")
    if token != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# Supabase импорты
if USE_SUPABASE:
    from supabase_client import (
        get_connection, get_all_tickets_raw, get_tickets_summary,
        get_support_stats, get_label_stats, _get, _patch
    )
else:
    from database import get_connection

CACHE_TTL = 30

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

dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard")
if os.path.exists(dashboard_path):
    app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

_summary_cache = {"data": None, "timestamp": 0}

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
    team_name: Optional[str] = None


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
    date: Optional[str] = None  # YYYY-MM-DD, по умолчанию сегодня


# ─────────────────────────────────────────────
# Эндпоинты — Тикеты
# ─────────────────────────────────────────────

@app.get("/api/tickets", response_model=TicketListResponse)
def get_tickets(
    status: Optional[str] = Query(None),
    support: Optional[str] = Query(None),
    label: Optional[str] = Query(None),
    trader_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=500),
):
    offset = (page - 1) * per_page

    if USE_SUPABASE:
        rows, total = get_all_tickets_raw(
            limit=per_page, offset=offset,
            status=status, taken_by=support, label=label, trader_id=trader_id
        )
    else:
        conn = get_connection()
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

        with conn:
            total = conn.execute(f"SELECT COUNT(*) FROM tickets WHERE {where_clause}", params).fetchone()[0]
            rows_raw = conn.execute(
                f"SELECT * FROM tickets WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params + [per_page, offset]
            ).fetchall()
        rows = [_row_to_dict(row) for row in rows_raw]

    tickets = [_row_to_ticket(r) for r in rows]
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return TicketListResponse(
        tickets=tickets, total=total, page=page, per_page=per_page, total_pages=total_pages
    )


@app.get("/api/tickets/open", response_model=list[TicketResponse])
def get_open_tickets():
    rows = database.get_open_tickets()
    if USE_SUPABASE:
        return [_row_to_ticket(r) for r in rows]
    return [_row_to_ticket(_row_to_dict(r)) for r in rows]


@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int):
    row = database.get_ticket(ticket_id)
    if not row:
        raise HTTPException(status_code=404, detail="Тикет не найден")
    if USE_SUPABASE:
        return _row_to_ticket(row)
    return _row_to_ticket(_row_to_dict(row))


@app.post("/api/tickets/{ticket_id}/take")
def take_ticket_api(ticket_id: int, support_username: str = "dashboard_user"):
    database.take_ticket(ticket_id, support_username, 0)

    # Получаем тикет для отправки уведомления
    ticket = database.get_ticket(ticket_id)
    if ticket and ticket.get("trader_chat_id"):
        label = ticket.get("label") or "Обращение"
        send_telegram_message(
            ticket["trader_chat_id"],
            f"🔧 <b>Ваша заявка #{ticket_id} взята в работу</b>\n\n📋 Тип: {label}\n👨‍💼 Саппорт: @{support_username}\n\nОжидайте ответа в поддержке."
        )

    return {"success": True, "status": "in_progress"}


@app.post("/api/tickets/{ticket_id}/close")
def close_ticket_api(ticket_id: int, support_username: str = "dashboard_user"):
    database.close_ticket(ticket_id)

    # Получаем тикет для отправки уведомления
    ticket = database.get_ticket(ticket_id)
    if ticket and ticket.get("trader_chat_id"):
        label = ticket.get("label") or "Обращение"
        send_telegram_message(
            ticket["trader_chat_id"],
            f"✅ <b>Ваша заявка #{ticket_id} закрыта</b>\n\n📋 Тип: {label}\n👨‍💼 Саппорт: @{support_username}\n\nЕсли остались вопросы — создайте новое обращение."
        )

    return {"success": True, "status": "closed"}


# ─────────────────────────────────────────────
# Эндпоинты — Статистика
# ─────────────────────────────────────────────

@app.get("/api/supports")
def get_supports():
    if USE_SUPABASE:
        from supabase_client import get_all_supports
        supports = get_all_supports()
        return [{"username": s.get("username", "")} for s in supports]
    else:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT taken_by FROM tickets
                WHERE taken_by IS NOT NULL AND taken_by != ''
                ORDER BY taken_by
            """).fetchall()
            return [{"username": row[0]} for row in rows]


@app.get("/api/chats")
def get_chats():
    """Получить список команд (чатов)."""
    if USE_SUPABASE:
        from supabase_client import get_all_chats
        return get_all_chats()
    else:
        # Для SQLite возвращаем пустой список (таблица chats не создаётся)
        return []


@app.get("/api/stats", response_model=list[SupportStats])
def get_stats():
    if USE_SUPABASE:
        rows = get_support_stats()
        return [SupportStats(
            username=r.get("username") or "unknown",
            total=r.get("total") or 0,
            closed=r.get("closed") or 0,
            in_progress=0,
            avg_seconds=r.get("avg_seconds")
        ) for r in rows]
    else:
        with get_connection() as conn:
            rows = conn.execute("""
                SELECT taken_by, COUNT(*) as total,
                       SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) as closed,
                       SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) as in_progress,
                       AVG(CASE WHEN status='closed' AND taken_at IS NOT NULL AND closed_at IS NOT NULL
                                THEN (julianday(closed_at) - julianday(taken_at)) * 86400 END) as avg_seconds
                FROM tickets WHERE taken_by IS NOT NULL GROUP BY taken_by ORDER BY total DESC
            """).fetchall()
            return [SupportStats(
                username=row[0] or "unknown", total=row[1] or 0, closed=row[2] or 0,
                in_progress=row[3] or 0, avg_seconds=row[4]
            ) for row in rows]


@app.get("/api/stats/{username}", response_model=SupportStats)
def get_support_stats_endpoint(username: str):
    stats = database.get_support_personal_stats(username)
    return SupportStats(
        username=username, total=stats["total"], closed=stats["closed"],
        in_progress=stats.get("in_progress", 0), avg_seconds=stats["avg_seconds"]
    )


@app.get("/api/commands", response_model=list[CommandInfo])
def get_commands():
    if USE_SUPABASE:
        rows = get_label_stats()
        count_map = {r[0]: r[1] for r in rows}
    else:
        with get_connection() as conn:
            rows = conn.execute("SELECT label, COUNT(*) as cnt FROM tickets GROUP BY label").fetchall()
            count_map = {row[0]: row[1] for row in rows}

    result = []
    for key, config in COMMANDS_CONFIG.items():
        result.append(CommandInfo(
            key=key, label=config["label"],
            needs_order_id=config["needs_order_id"],
            ticket_count=count_map.get(config["label"], 0)
        ))
    result.sort(key=lambda x: x.ticket_count, reverse=True)
    return result


# ─────────────────────────────────────────────
# Эндпоинты — Дежурство
# ─────────────────────────────────────────────

@app.get("/api/duty", response_model=DutyResponse)
def get_duty():
    duty_info = schedule_manager.get_duty_info()
    return DutyResponse(
        support_username=", ".join(duty_info["names"]) if duty_info["names"] else None,
        shift=duty_info["shift"]
    )


@app.get("/api/schedule")
def get_schedule(offset: int = Query(0, description="Смещение недели (0 = текущая)")):
    week = schedule_manager.get_week_schedule(offset)
    return {"week": week, "today": datetime.now().strftime("%Y-%m-%d"), "offset": offset}


@app.post("/api/duty")
def set_duty_endpoint(req: SetDutyRequest):
    now = datetime.now()
    date_str = req.date or now.strftime("%Y-%m-%d")
    shift = req.shift or ("day" if 9 <= now.hour < 21 else "night")

    if USE_SUPABASE:
        from supabase_client import set_duty as sb_set_duty
        sb_set_duty(date_str, shift, [req.support_username])
    else:
        schedule_manager.set_duty(date_str, shift, [req.support_username])

    return {"success": True, "support_username": req.support_username, "shift": shift, "date": date_str}


@app.post("/api/duty/switch")
def switch_duty():
    """Смена дежурных + рассылка во все чаты."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hour = now.hour

    # Определяем новую смену
    new_shift = "day" if 9 <= hour < 21 else "night"
    shift_label = "☀️ Дневная" if new_shift == "day" else "🌙 Ночная"

    # Получаем дежурных на эту смену
    if USE_SUPABASE:
        from supabase_client import get_all_chats
        duty = schedule_manager.get_current_duty()
    else:
        duty = schedule_manager.get_current_duty()

    duty_names = ", ".join([f"@{d}" for d in duty]) if duty else "никто"

    # Получаем все чаты для рассылки
    if USE_SUPABASE:
        from supabase_client import get_all_chats
        chats = get_all_chats()
    else:
        chats = []

    # Формируем сообщение
    message = f"🔔 <b>Коллега, персменка, сейчас на посту {duty_names}!</b>"

    # Рассылаем во все чаты
    sent = 0
    for chat in chats:
        chat_id = chat.get("chat_id")
        if chat_id:
            if send_telegram_message(chat_id, message):
                sent += 1

    return {
        "success": True,
        "shift": new_shift,
        "duty": duty,
        "chats_notified": sent
    }


# ─────────────────────────────────────────────
# Эндпоинты — Сводка
# ─────────────────────────────────────────────

@app.get("/api/summary")
def get_summary():
    global _summary_cache
    cache_now = time.time()

    if _summary_cache["data"] and (cache_now - _summary_cache["timestamp"]) < CACHE_TTL:
        return _summary_cache["data"]

    if USE_SUPABASE:
        summary = get_tickets_summary()
        labels = get_label_stats()

        # Получаем все тикеты для анализа
        all_tickets = _get("/tickets?select=created_at")
        MSK = pytz.timezone("Europe/Moscow")
        now = datetime.now(MSK)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)

        by_hour = {}
        by_day = {}
        for t in all_tickets:
            try:
                created = datetime.fromisoformat(t["created_at"].replace("Z", "+00:00"))
                created_msk = created.astimezone(MSK)
                if created_msk >= day_ago:
                    hour_key = created_msk.strftime("%H")
                    by_hour[hour_key] = by_hour.get(hour_key, 0) + 1
                if created_msk >= week_ago:
                    day_key = created_msk.strftime("%Y-%m-%d")
                    by_day[day_key] = by_day.get(day_key, 0) + 1
            except:
                pass

        by_hour = [(f"{h:02d}", by_hour.get(h, 0)) for h in range(24)]
        by_day = sorted(by_day.items())
    else:
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            open_count = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0]
            in_progress = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'").fetchone()[0]
            closed = conn.execute("SELECT COUNT(*) FROM tickets WHERE status='closed'").fetchone()[0]
            summary = {"total": total, "open": open_count, "in_progress": in_progress, "closed": closed, "today": 0}

            labels = conn.execute("SELECT label, COUNT(*) as cnt FROM tickets GROUP BY label ORDER BY cnt DESC").fetchall()
            by_hour = conn.execute("""
                SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt
                FROM tickets WHERE created_at >= datetime('now', '-1 day') GROUP BY hour ORDER BY hour
            """).fetchall()
            by_day = conn.execute("""
                SELECT strftime('%Y-%m-%d', created_at) as day, COUNT(*) as cnt
                FROM tickets WHERE created_at >= datetime('now', '-7 days') GROUP BY day ORDER BY day
            """).fetchall()

    duty = schedule_manager.get_current_duty()

    result = {
        "total": summary.get("total", 0),
        "open": summary.get("open", 0),
        "in_progress": summary.get("in_progress", 0),
        "closed": summary.get("closed", 0),
        "by_label": [{"label": r[0], "count": r[1]} for r in labels],
        "by_hour": [{"hour": str(r[0]).zfill(2), "count": r[1]} for r in by_hour],
        "by_day": [{"day": str(r[0]), "count": r[1]} for r in by_day],
        "current_duty": ", ".join(duty) if duty else None
    }

    _summary_cache = {"data": result, "timestamp": cache_now}
    return result


# ─────────────────────────────────────────────
# Мониторинг
# ─────────────────────────────────────────────

@app.get("/api/check_alerts")
def check_stale_tickets():
    """Проверяет тикеты старше 12 минут и отправляет алерты."""
    if not BOT_TOKEN:
        return {"success": False, "error": "BOT_TOKEN not configured"}

    from supabase_client import _get, _patch

    # Находим тикеты старше 12 минут
    stale_tickets = _get(
        "/tickets?status=eq.open&alert_sent=eq.false&"
        "created_at=lt.now()%20-%20interval%20%2712%20minutes%27"
        "&select=id,label,trader_username,created_at,trader_chat_id"
    )

    sent_count = 0
    for ticket in stale_tickets:
        ticket_id = ticket.get("id")
        label = ticket.get("label") or "Обращение"
        trader_username = ticket.get("trader_username") or "unknown"
        trader_chat_id = ticket.get("trader_chat_id")

        # Считаем минуты
        try:
            created = datetime.fromisoformat(ticket.get("created_at", "").replace("Z", "+00:00"))
            minutes_ago = int((datetime.now() - created).total_seconds() / 60)
        except:
            minutes_ago = 12

        # Отправляем в саппорт-чат
        support_message = (
            f"⚠️ <b>Тикет #{ticket_id} не взят!</b>\n\n"
            f"📋 {label}\n"
            f"👤 @{trader_username}\n"
            f"⏱️ {minutes_ago} мин"
        )
        send_telegram_message(SUPPORT_CHAT_ID, support_message)

        # Уведомляем трейдера
        if trader_chat_id:
            trader_message = (
                f"⏰ <b>Напоминание по заявке #{ticket_id}</b>\n\n"
                f"Ваша заявка \"{label}\" ещё не взята в работу.\n"
                f"Пожалуйста, ожидайте — саппорт скоро ответит."
            )
            send_telegram_message(trader_chat_id, trader_message)

        # Отмечаем что алерт отправлен
        _patch(f"/tickets?id=eq.{ticket_id}", {"alert_sent": True})
        sent_count += 1
        logger.info(f"Alert sent for ticket #{ticket_id}")

    return {"success": True, "alerts_sent": sent_count}


@app.get("/health")
def health_check():
    try:
        if USE_SUPABASE:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        else:
            with get_connection() as conn:
                conn.execute("SELECT 1")
        return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "2.0.0", "db": "supabase" if USE_SUPABASE else "sqlite"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}


@app.get("/api/stats_summary")
def get_stats_summary():
    try:
        if USE_SUPABASE:
            s = get_tickets_summary()
            return {**s, "timestamp": datetime.now().isoformat()}
        else:
            with get_connection() as conn:
                return {
                    "total": conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0],
                    "open": conn.execute("SELECT COUNT(*) FROM tickets WHERE status='open'").fetchone()[0],
                    "in_progress": conn.execute("SELECT COUNT(*) FROM tickets WHERE status='in_progress'").fetchone()[0],
                    "closed": conn.execute("SELECT COUNT(*) FROM tickets WHERE status='closed'").fetchone()[0],
                    "timestamp": datetime.now().isoformat()
                }
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    """Конвертирует sqlite3.Row в dict."""
    if isinstance(row, dict):
        return row
    return dict(row)


def _row_to_ticket(row: dict) -> TicketResponse:
    """Конвертирует dict в TicketResponse."""
    return TicketResponse(
        id=row.get("id"),
        trader_id=row.get("trader_id"),
        trader_username=row.get("trader_username") or "",
        trader_name=row.get("trader_name") or "",
        label=row.get("label") or "",
        order_id=row.get("order_id"),
        status=row.get("status") or "open",
        taken_by=row.get("taken_by"),
        taken_at=str(row.get("taken_at")) if row.get("taken_at") else None,
        closed_at=str(row.get("closed_at")) if row.get("closed_at") else None,
        created_at=str(row.get("created_at")) if row.get("created_at") else "",
        trader_chat_id=row.get("trader_chat_id"),
        team_name=row.get("team_name")
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
