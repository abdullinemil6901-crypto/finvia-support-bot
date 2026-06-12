"""
Supabase клиент для Support Bot.
Использует REST API через requests.
"""
import os
import requests
from datetime import datetime
import pytz

# Загружаем .env если есть
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Настройки — из переменных окружения (.env)
PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "")
API_KEY = os.getenv("SUPABASE_API_KEY", "")
BASE_URL = f"https://{PROJECT_REF}.supabase.co/rest/v1"

HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

MSK = pytz.timezone("Europe/Moscow")


def _get(endpoint: str, params: dict = None) -> list:
    resp = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json() if resp.text else []


def _post(endpoint: str, data: dict) -> dict:
    resp = requests.post(f"{BASE_URL}{endpoint}", headers=HEADERS, json=data)
    resp.raise_for_status()
    result = resp.json()
    # Supabase возвращает массив для INSERT
    if isinstance(result, list):
        return result[0] if result else {}
    return result


def _patch(endpoint: str, data: dict, params: dict = None) -> dict:
    resp = requests.patch(
        f"{BASE_URL}{endpoint}",
        headers={**HEADERS, "Prefer": "return=representation"},
        json=data,
        params=params
    )
    resp.raise_for_status()
    return resp.json()


def _delete(endpoint: str, params: dict = None):
    resp = requests.delete(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params)
    return resp.status_code in (200, 204, 406)  # 406 если не найден


# ============================================
# TICKETS
# ============================================

def save_ticket(
    trader_id: int,
    trader_username: str,
    trader_name: str,
    label: str,
    order_id: str = None,
    trader_chat_id: int = None,
    team_name: str = None
) -> int:
    data = {
        "trader_id": trader_id,
        "trader_username": trader_username or "",
        "trader_name": trader_name or "",
        "label": label,
        "order_id": order_id,
        "trader_chat_id": trader_chat_id,
        "team_name": team_name,
        "status": "open",
        "created_at": datetime.now().isoformat()
    }
    result = _post("/tickets", data)
    return result["id"]


def take_ticket(ticket_id: int, support_username: str, support_id: int):
    _patch("/tickets", {
        "status": "in_progress",
        "taken_by": support_username,
        "taken_by_id": support_id,
        "taken_at": datetime.now().isoformat()
    }, params={"id": f"eq.{ticket_id}"})


def close_ticket(ticket_id: int):
    _patch("/tickets", {
        "status": "closed",
        "closed_at": datetime.now().isoformat()
    }, params={"id": f"eq.{ticket_id}"})


def get_ticket(ticket_id: int):
    result = _get(f"/tickets?id=eq.{ticket_id}")
    return result[0] if result else None


def get_open_tickets() -> list:
    return _get("/tickets?status=eq.open&order=created_at.asc",
                params={"select": "id,trader_id,trader_username,trader_name,label,order_id,created_at,trader_chat_id"})


def get_all_tickets(limit: int = 100) -> list:
    return _get(f"/tickets?order=created_at.desc&limit={limit}")


def get_tickets_by_support(support_username: str) -> list:
    return _get(f"/tickets?taken_by=eq.{support_username}&order=created_at.desc")


def get_trader_tickets(trader_id: int) -> list:
    return _get(f"/tickets?trader_id=eq.{trader_id}&order=created_at.desc",
               params={"select": "id,label,order_id,status,taken_by,created_at,closed_at"})


def get_support_personal_stats(support_username: str) -> dict:
    tickets = _get(f"/tickets?taken_by=eq.{support_username}")
    total = len(tickets)
    closed = sum(1 for t in tickets if t.get("status") == "closed")
    in_progress = sum(1 for t in tickets if t.get("status") == "in_progress")

    # Среднее время закрытия
    closed_with_time = [
        (datetime.fromisoformat(t["closed_at"]) - datetime.fromisoformat(t["taken_at"])).total_seconds()
        for t in tickets
        if t.get("status") == "closed" and t.get("taken_at") and t.get("closed_at")
    ]
    avg_seconds = sum(closed_with_time) / len(closed_with_time) if closed_with_time else None

    return {"total": total, "closed": closed, "in_progress": in_progress, "avg_seconds": avg_seconds}


def get_label_stats() -> list:
    tickets = _get("/tickets")
    from collections import Counter
    counts = Counter(t.get("label") for t in tickets)
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)


def get_hourly_stats() -> list:
    tickets = _get("/tickets")
    from collections import Counter
    hours = [datetime.fromisoformat(t["created_at"]).strftime("%H") for t in tickets]
    counts = Counter(hours)
    return [(f"{h:02d}", counts.get(h, 0)) for h in range(24)]


# ============================================
# SUPPORTS
# ============================================

def add_support(tg_id: int, username: str, full_name: str):
    _post("/supports", {
        "tg_id": tg_id,
        "username": username,
        "full_name": full_name,
        "added_at": datetime.now().isoformat()
    })


def get_all_supports() -> list:
    return _get("/supports?order=added_at.desc")


def get_support_by_tg_id(tg_id: int):
    result = _get(f"/supports?tg_id=eq.{tg_id}")
    return result[0] if result else None


def remove_support(tg_id: int):
    _delete(f"/supports?tg_id=eq.{tg_id}")


# ============================================
# EVENTS
# ============================================

def log_event(event_type: str, user_id: int, username: str = None):
    _post("/events", {
        "event_type": event_type,
        "user_id": user_id,
        "username": username,
        "created_at": datetime.now().isoformat()
    })


def get_today_stats() -> dict:
    today = datetime.now(MSK).strftime("%Y-%m-%d")
    events = _get(f"/events?created_at=gte.{today}T00:00:00")
    from collections import Counter
    counts = Counter(e.get("event_type") for e in events)
    return dict(counts)


# ============================================
# DUTY SCHEDULE
# ============================================

def set_duty(date: str, shift_type: str, names: list):
    # Upsert
    existing = _get(f"/duty_schedule?date=eq.{date}&shift_type=eq.{shift_type}")
    if existing:
        _patch(f"/duty_schedule?date=eq.{date}&shift_type=eq.{shift_type}", {"names": names})
    else:
        _post("/duty_schedule", {"date": date, "shift_type": shift_type, "names": names})


def get_current_duty() -> list:
    today = datetime.now(MSK).strftime("%Y-%m-%d")
    hour = datetime.now(MSK).hour
    shift_type = "day" if 9 <= hour < 21 else "night"

    result = _get(f"/duty_schedule?date=eq.{today}&shift_type=eq.{shift_type}")
    if result:
        return result[0].get("names", [])
    return []


def get_week_schedule() -> list:
    today = datetime.now(MSK).strftime("%Y-%m-%d")
    return _get(f"/duty_schedule?date=gte.{today}&order=date.asc,shift_type.asc")


# ============================================
# ANALYTICS
# ============================================

def get_tickets_summary() -> dict:
    tickets = _get("/tickets?select=status,created_at")
    total = len(tickets)
    open_count = sum(1 for t in tickets if t.get("status") == "open")
    in_progress = sum(1 for t in tickets if t.get("status") == "in_progress")
    closed = sum(1 for t in tickets if t.get("status") == "closed")

    today = datetime.now(MSK).strftime("%Y-%m-%d")
    today_count = sum(1 for t in tickets if t.get("created_at", "").startswith(today))

    return {"total": total, "open": open_count, "in_progress": in_progress, "closed": closed, "today": today_count}


def get_support_stats() -> list:
    tickets = _get("/tickets?select=taken_by,status,taken_at,closed_at")
    # Фильтруем на стороне клиента
    tickets = [t for t in tickets if t.get("taken_by")]
    from collections import defaultdict
    from statistics import mean

    stats = defaultdict(lambda: {"total": 0, "closed": 0, "times": []})

    for t in tickets:
        username = t.get("taken_by")
        stats[username]["total"] += 1
        if t.get("status") == "closed":
            stats[username]["closed"] += 1
            if t.get("taken_at") and t.get("closed_at"):
                try:
                    sec = (datetime.fromisoformat(t["closed_at"]) - datetime.fromisoformat(t["taken_at"])).total_seconds()
                    stats[username]["times"].append(sec)
                except:
                    pass

    result = []
    for username, s in stats.items():
        result.append({
            "username": username,
            "total": s["total"],
            "closed": s["closed"],
            "avg_seconds": mean(s["times"]) if s["times"] else None
        })

    return sorted(result, key=lambda x: x["total"], reverse=True)


def get_all_tickets_raw(limit: int = 100, offset: int = 0, **filters) -> tuple:
    """Получить тикеты с фильтрами. Возвращает (rows, total)."""
    conditions = []
    params = []

    if filters.get("status"):
        conditions.append(f"status=eq.{filters['status']}")
    if filters.get("taken_by"):
        conditions.append(f"taken_by=eq.{filters['taken_by']}")
    if filters.get("label"):
        conditions.append(f"label=eq.{filters['label']}")
    if filters.get("trader_id"):
        conditions.append(f"trader_id=eq.{filters['trader_id']}")

    filter_str = "&".join(conditions) if conditions else ""

    # Total
    total = len(_get(f"/tickets?{filter_str}" if filter_str else "/tickets"))

    # Rows with pagination
    rows = _get(f"/tickets?{filter_str}&order=created_at.desc&limit={limit}&offset={offset}" if filter_str else f"/tickets?order=created_at.desc&limit={limit}&offset={offset}")

    return rows, total


def get_connection():
    """Stub для совместимости."""
    return None


# ============================================
# CHATS (команды трейдеров)
# ============================================

def get_all_chats() -> list:
    """Получить все чаты."""
    return _get("/chats?is_active=eq.true&order=team_name.asc")


def get_chat_by_id(chat_id: int) -> dict:
    """Найти чат по chat_id."""
    result = _get(f"/chats?chat_id=eq.{chat_id}")
    return result[0] if result else None


def save_chat(chat_id: int, team_name: str) -> dict:
    """Сохранить или обновить чат (upsert)."""
    data = {
        "chat_id": chat_id,
        "team_name": team_name,
        "is_active": True
    }
    result = _post("/chats", data)
    return result


def deactivate_chat(chat_id: int):
    """Отключить чат (бот удалён)."""
    _patch(f"/chats?chat_id=eq.{chat_id}", {"is_active": False})