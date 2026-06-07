from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import ADMIN_IDS, TYPE_LABELS
from db import log_event, get_today_stats
from charts import generate_report_charts
from schedule_manager import get_current_duty

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    commands = "\n".join([f"/{cmd} — {label}" for cmd, label in TYPE_LABELS.items()])
    await message.answer(f"Привет! Я бот саппорт-команды.\n\nДоступные команды:\n{commands}\n\n/report — отчёт за сегодня\n/duty — кто сейчас дежурит")

@router.message(Command("cancel_payment"))
async def cmd_cancel_payment(message: Message):
    log_event("cancel_payment", message.from_user.id, message.from_user.username)
    await message.answer("✅ Обращение «Отмена платежа» зафиксировано.")

@router.message(Command("wrong_cvu"))
async def cmd_wrong_cvu(message: Message):
    log_event("wrong_cvu", message.from_user.id, message.from_user.username)
    await message.answer("✅ Обращение «Неверный CVU» зафиксировано.")

@router.message(Command("no_receipt"))
async def cmd_no_receipt(message: Message):
    log_event("no_receipt", message.from_user.id, message.from_user.username)
    await message.answer("✅ Обращение «Нет чека» зафиксировано.")

@router.message(Command("report"))
async def cmd_report(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У тебя нет доступа к этой команде.")
        return
    stats = get_today_stats()
    if not stats:
        await message.answer("За сегодня обращений не было.")
        return
    photos = generate_report_charts(stats)
    for photo in photos:
        await message.answer_photo(photo)

@router.message(Command("duty"))
async def cmd_duty(message: Message):
    duty_info = get_current_duty()
    if not duty_info:
        await message.answer("Расписание дежурных не задано.")
    else:
        await message.answer(f"👤 Сейчас дежурят: {', '.join(duty_info)}")

@router.message(Command("set_duty"))
async def cmd_set_duty(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У тебя нет доступа к этой команде.")
        return
    parts = message.text.split()[1:]
    if len(parts) < 3:
        await message.answer("Формат: /set_duty YYYY-MM-DD day/night Имя1 Имя2")
        return
    date, shift, *names = parts
    from schedule_manager import set_duty
    set_duty(date, shift, names)
    await message.answer(f"✅ Расписание обновлено: {date} {shift} — {', '.join(names)}")
