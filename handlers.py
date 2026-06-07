from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from config import ADMIN_IDS, TYPE_LABELS, BOT_TOKEN
from db import log_event, get_today_stats
from charts import generate_report_charts
from schedule_manager import get_current_duty

SUPPORT_CHAT_ID = -5160275115  # Саппортский чат

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🌟 <b>Finvia P2P — Служба поддержки</b>\n\n"
        "Добро пожаловать! Я ваш персональный ассистент саппорт-команды.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💼 <b>Что я умею:</b>\n"
        "• Фиксирую обращения клиентов\n"
        "• Веду статистику по типам проблем\n"
        "• Показываю дежурного оператора\n"
        "• Генерирую отчёты для команды\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Выберите тип обращения из меню ниже 👇",
        parse_mode="HTML"
    )

async def notify_support(bot: Bot, event_type: str, user_id: int, username: str):
    label = TYPE_LABELS.get(event_type, event_type)
    uname = f"@{username}" if username else f"id:{user_id}"
    text = (
        f"📥 <b>Новая заявка</b>\n\n"
        f"📌 Тип: <b>{label}</b>\n"
        f"👤 Трейдер: {uname}\n"
        f"🆔 ID: {user_id}"
    )
    await bot.send_message(SUPPORT_CHAT_ID, text, parse_mode="HTML")

@router.message(Command("cancel_payment"))
async def cmd_cancel_payment(message: Message, bot: Bot):
    log_event("cancel_payment", message.from_user.id, message.from_user.username)
    await message.answer("✅ Обращение «Отмена платежа» зафиксировано.")
    await notify_support(bot, "cancel_payment", message.from_user.id, message.from_user.username)

@router.message(Command("wrong_cvu"))
async def cmd_wrong_cvu(message: Message, bot: Bot):
    log_event("wrong_cvu", message.from_user.id, message.from_user.username)
    await message.answer("✅ Обращение «Неверный CVU» зафиксировано.")
    await notify_support(bot, "wrong_cvu", message.from_user.id, message.from_user.username)

@router.message(Command("no_receipt"))
async def cmd_no_receipt(message: Message, bot: Bot):
    log_event("no_receipt", message.from_user.id, message.from_user.username)
    await message.answer("✅ Обращение «Нет чека» зафиксировано.")
    await notify_support(bot, "no_receipt", message.from_user.id, message.from_user.username)

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
