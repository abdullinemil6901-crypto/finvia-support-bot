import json
import os
from datetime import datetime, timedelta
import pytz
import requests

SCHEDULE_PATH = "schedule.json"
MSK = pytz.timezone("Europe/Moscow")

USE_SUPABASE = bool(os.getenv("SUPABASE_API_KEY") and os.getenv("SUPABASE_PROJECT_REF"))


def _sb_get(endpoint: str) -> list:
    """GET запрос к Supabase."""
    if not USE_SUPABASE:
        return []
    base_url = f"https://{os.getenv('SUPABASE_PROJECT_REF')}.supabase.co/rest/v1"
    headers = {
        "apikey": os.getenv("SUPABASE_API_KEY", ""),
        "Authorization": f"Bearer {os.getenv('SUPABASE_API_KEY', '')}"
    }
    resp = requests.get(f"{base_url}{endpoint}", headers=headers)
    return resp.json() if resp.ok else []


def _sb_post(endpoint: str, data: dict):
    """POST запрос к Supabase."""
    if not USE_SUPABASE:
        return
    base_url = f"https://{os.getenv('SUPABASE_PROJECT_REF')}.supabase.co/rest/v1"
    headers = {
        "apikey": os.getenv("SUPABASE_API_KEY", ""),
        "Authorization": f"Bearer {os.getenv('SUPABASE_API_KEY', '')}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    requests.post(f"{base_url}{endpoint}", headers=headers, json=data)


def _sb_patch(endpoint: str, data: dict):
    """PATCH запрос к Supabase."""
    if not USE_SUPABASE:
        return
    base_url = f"https://{os.getenv('SUPABASE_PROJECT_REF')}.supabase.co/rest/v1"
    headers = {
        "apikey": os.getenv("SUPABASE_API_KEY", ""),
        "Authorization": f"Bearer {os.getenv('SUPABASE_API_KEY', '')}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    requests.patch(f"{base_url}{endpoint}", headers=headers, json=data)


# ─────────────────────────────────────────────
# Локальные функции (fallback)
# ─────────────────────────────────────────────

def load_schedule() -> dict:
    if not os.path.exists(SCHEDULE_PATH):
        return {}
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schedule(schedule: dict):
    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# Основные функции
# ─────────────────────────────────────────────

def get_current_shift() -> tuple:
    now = datetime.now(MSK)
    hour = now.hour
    if 9 <= hour < 21:
        return ("day", "09:00", "21:00")
    else:
        return ("night", "21:00", "09:00")


def get_current_duty() -> list:
    """Получить текущего дежурного из Supabase."""
    now = datetime.now(MSK)
    date_str = now.strftime("%Y-%m-%d")
    shift_type = "day" if 9 <= now.hour < 21 else "night"

    if USE_SUPABASE:
        result = _sb_get(f"/duty_schedule?date=eq.{date_str}&shift_type=eq.{shift_type}&limit=1")
        if result:
            return result[0].get("names", [])
        return []

    # Fallback
    schedule = load_schedule()
    return schedule.get(date_str, {}).get(shift_type, [])


def get_duty_info() -> dict:
    """Расширенная информация о текущем дежурстве."""
    now = datetime.now(MSK)
    shift_type, start_time, end_time = get_current_shift()
    duty = get_current_duty()

    return {
        "names": duty,
        "shift": shift_type,
        "shift_label": "Дневная" if shift_type == "day" else "Ночная",
        "start_time": start_time,
        "end_time": end_time,
        "current_time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
    }


def get_week_schedule(week_offset: int = 0) -> list:
    """Расписание на неделю."""
    now = datetime.now(MSK)
    start_of_week = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)

    if USE_SUPABASE:
        start_date = start_of_week.strftime("%Y-%m-%d")
        end_date = (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d")
        result = _sb_get(f"/duty_schedule?date=gte.{start_date}&date=lte.{end_date}&order=date.asc,shift_type.asc")

        schedule_map = {}
        for row in result:
            date = row.get("date")
            shift = row.get("shift_type")
            names = row.get("names", [])
            if date:
                if date not in schedule_map:
                    schedule_map[date] = {"day": [], "night": []}
                if shift == "day":
                    schedule_map[date]["day"] = names
                elif shift == "night":
                    schedule_map[date]["night"] = names

        week_schedule = []
        for i in range(7):
            day = start_of_week + timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            day_data = schedule_map.get(date_str, {"day": [], "night": []})
            week_schedule.append({
                "date": date_str,
                "day_name": day.strftime("%a"),
                "day_label": day.strftime("%d.%m"),
                "day": day_data["day"],
                "night": day_data["night"],
                "is_today": date_str == now.strftime("%Y-%m-%d"),
            })
        return week_schedule

    # Fallback
    schedule = load_schedule()
    week_schedule = []
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        day_schedule = schedule.get(date_str, {})
        week_schedule.append({
            "date": date_str,
            "day_name": day.strftime("%a"),
            "day_label": day.strftime("%d.%m"),
            "day": day_schedule.get("day", []),
            "night": day_schedule.get("night", []),
            "is_today": date_str == now.strftime("%Y-%m-%d"),
        })
    return week_schedule


def set_duty(date: str, shift: str, names: list):
    """Сохранить дежурного в Supabase."""
    if USE_SUPABASE:
        existing = _sb_get(f"/duty_schedule?date=eq.{date}&shift_type=eq.{shift}&limit=1")
        if existing:
            _sb_patch(f"/duty_schedule?date=eq.{date}&shift_type=eq.{shift}", {"names": names})
        else:
            _sb_post("/duty_schedule", {"date": date, "shift_type": shift, "names": names})
        return

    # Fallback
    schedule = load_schedule()
    if date not in schedule:
        schedule[date] = {}
    schedule[date][shift] = names
    save_schedule(schedule)
