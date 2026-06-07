import json
import os
from datetime import datetime
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

def get_current_duty() -> list:
    now = datetime.now(MSK)
    date_str = now.strftime("%Y-%m-%d")
    hour = now.hour
    shift = "day" if 9 <= hour < 21 else "night"
    schedule = load_schedule()
    return schedule.get(date_str, {}).get(shift, [])

def set_duty(date: str, shift: str, names: list):
    schedule = load_schedule()
    if date not in schedule:
        schedule[date] = {}
    schedule[date][shift] = names
    save_schedule(schedule)
