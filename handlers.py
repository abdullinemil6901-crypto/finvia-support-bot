from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS, TYPE_LABELS, BOT_TOKEN
from db import log_event, get_today_stats
from charts import generate_report_charts
from schedule_manager import get_current_duty

SUPPORT_CHAT_ID = -5160275115  # Саппортский чат
TRADER_GROUP_ID = -1001234567890  # ID группы трейдеров (замените на реальный)

router = Router()

# Статусы агентов
agent_statuses = {}

class ApplicationForm(StatesGroup):
    waiting_for_type = State()
    waiting_for_description = State()
    waiting_for_amount = State()

def get_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена платежа", callback_data="apply_cancel_payment")],
        [InlineKeyboardButton(text="🔢 Неверный CVU", callback_data="apply_wrong_cvu")],
        [InlineKeyboardButton(text="🧾 Нет чека", callback_data="apply_no_receipt")],
        [InlineKeyboardButton(text="💬 Другое", callback_data="apply_other")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard(event_type: str) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{event_type}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_form"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def is_trader(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(TRADER_GROUP_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

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
