import json
import os
from datetime import datetime, timedelta
import pytz

SCHEDULE_PATH = "schedule.json"
MSK = pytz.timezone("Europe/Moscow")


def load_schedule() -> dict:
    if not os.path.exists(SCHEDULE_PATH):
        return {}
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_schedule(schedule: dict):
    with open(SCHEDULE_PATH, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)


def get_current_shift() -> tuple[str, str, str]:
    """
    Returns: (shift_type, start_time, end_time)
    shift_type: 'day' или 'night'
    start_time: "09:00"
    end_time: "21:00" или "09:00"
    """
    now = datetime.now(MSK)
    hour = now.hour
    if 9 <= hour < 21:
        return ("day", "09:00", "21:00")
    else:
        return ("night", "21:00", "09:00")


def get_current_duty() -> list:
    now = datetime.now(MSK)
    date_str = now.strftime("%Y-%m-%d")
    hour = now.hour
    shift = "day" if 9 <= hour < 21 else "night"
    schedule = load_schedule()
    return schedule.get(date_str, {}).get(shift, [])


def get_duty_info() -> dict:
    """
    Расширенная информация о текущем дежурстве.
    """
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
    """
    Returns schedule for current week (Mon-Sun).
    week_offset: 0 = текущая неделя, 1 = следующая, -1 = предыдущая
    """
    now = datetime.now(MSK)
    start_of_week = now - timedelta(days=now.weekday()) + timedelta(weeks=week_offset)
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
    schedule = load_schedule()
    if date not in schedule:
        schedule[date] = {}
    schedule[date][shift] = names
    save_schedule(schedule)
