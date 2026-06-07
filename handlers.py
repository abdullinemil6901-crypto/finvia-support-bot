from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import SUPPORT_CHAT_ID, ADMIN_IDS
from db import log_event, get_today_stats
from charts import generate_report_charts
from schedule_manager import get_current_duty, set_duty

router = Router()

TYPE_LABELS = {
    "cancel_payment": "Отмена платежа",
    "wrong_cvu": "Неверный CVU",
    "no_receipt": "Нет чека",
    "other": "Другое",
}

class ApplicationForm(StatesGroup):
    waiting_description = State()
    waiting_amount = State()
    waiting_screenshot = State()

def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена платежа", callback_data="apply_cancel_payment")],
        [InlineKeyboardButton(text="🔢 Неверный CVU", callback_data="apply_wrong_cvu")],
        [InlineKeyboardButton(text="🧾 Нет чека", callback_data="apply_no_receipt")],
        [InlineKeyboardButton(text="📝 Другое", callback_data="apply_other")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_form")]
    ])

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
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "apply_cancel_payment")
async def cb_cancel_payment(callback: CallbackQuery, bot: Bot):
    log_event("cancel_payment", callback.from_user.id, callback.from_user.username)
    await callback.message.answer(
        "✅ Обращение <b>«Отмена платежа»</b> зафиксировано.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏳ Ожидайте ответа от поддержки в течение 15 минут.\n"
        "💬 Если вопрос срочный — напишите в чат поддержки.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await notify_support(bot, "cancel_payment", callback.from_user.id, callback.from_user.username)
    await callback.answer()

@router.callback_query(F.data == "apply_wrong_cvu")
async def cb_wrong_cvu(callback: CallbackQuery, bot: Bot):
    log_event("wrong_cvu", callback.from_user.id, callback.from_user.username)
    await callback.message.answer(
        "✅ Обращение <b>«Неверный CVU»</b> зафиксировано.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏳ Ожидайте ответа от поддержки в течение 15 минут.\n"
        "💬 Если вопрос срочный — напишите в чат поддержки.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await notify_support(bot, "wrong_cvu", callback.from_user.id, callback.from_user.username)
    await callback.answer()

@router.callback_query(F.data == "apply_no_receipt")
async def cb_no_receipt(callback: CallbackQuery, bot: Bot):
    log_event("no_receipt", callback.from_user.id, callback.from_user.username)
    await callback.message.answer(
        "✅ Обращение <b>«Нет чека»</b> зафиксировано.\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏳ Ожидайте ответа от поддержки в течение 15 минут.\n"
        "💬 Если вопрос срочный — напишите в чат поддержки.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await notify_support(bot, "no_receipt", callback.from_user.id, callback.from_user.username)
    await callback.answer()

@router.callback_query(F.data == "apply_other")
async def cb_other(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ApplicationForm.waiting_description)
    await callback.message.answer(
        "📝 <b>Опишите вашу проблему подробно:</b>\n\n"
        "• Что произошло?\n"
        "• Какие действия вы предпринимали?\n"
        "• Что ожидали получить?",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(ApplicationForm.waiting_description)
async def process_description(message: Message, state: FSMContext):
    if message.text and len(message.text.strip()) < 10:
        await message.answer("⚠️ Пожалуйста, опишите проблему подробнее (минимум 10 символов).")
        return
    await state.update_data(description=message.text)
    await state.set_state(ApplicationForm.waiting_amount)
    await message.answer(
        "💰 <b>Укажите сумму сделки:</b>\n\n"
        "• Если сумма известна — введите её\n"
        "• Если не применимо — напишите «нет»",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(ApplicationForm.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await state.set_state(ApplicationForm.waiting_screenshot)
    await message.answer(
        "📎 <b>Прикрепите скриншот (необязательно):</b>\n\n"
        "• Отправьте фото, если есть скриншот\n"
        "• Или напишите «нет», чтобы пропустить",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )

@router.message(ApplicationForm.waiting_screenshot)
async def process_screenshot(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    description = data.get("description", "")
    amount = data.get("amount", "")

    log_event("other", message.from_user.id, message.from_user.username)

    uname = f"@{message.from_user.username}" if message.from_user.username else f"id:{message.from_user.id}"
    text = (
        f"📥 <b>Новая заявка</b>\n\n"
        f"📌 Тип: <b>Другое</b>\n"
        f"👤 Трейдер: {uname}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Описание:</b>\n{description}\n"
        f"💰 <b>Сумма:</b> {amount}"
    )

    if message.photo:
        await bot.send_photo(SUPPORT_CHAT_ID, message.photo[-1].file_id, caption=text, parse_mode="HTML")
    else:
        await bot.send_message(SUPPORT_CHAT_ID, text, parse_mode="HTML")

    await message.answer(
        "✅ <b>Обращение зафиксировано!</b>\n\n"
        "📋 Ваша заявка отправлена в саппорт-чат.\n"
        "⏳ Ожидайте ответа в течение 15 минут.\n\n"
        "💬 Если вопрос срочный — напишите напрямую.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    await state.clear()

@router.callback_query(F.data == "cancel_form")
async def cb_cancel_form(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "❌ Действие отменено.\n\n"
        "Вы можете начать заново или выбрать другую категорию.",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()

async def notify_support(bot: Bot, event_type: str, user_id: int, username: str):
    label = TYPE_LABELS.get(event_type, event_type)
    uname = f"@{username}" if username else f"id:{user_id}"
    text = (
        f"📥 <b>Новая заявка</b>\n\n"
        f"📌 Тип: <b>{label}</b>\n"
        f"👤 Трейдер: {uname}\n"
        f"🆔 ID: {user_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ Время: сейчас"
    )
    await bot.send_message(SUPPORT_CHAT_ID, text, parse_mode="HTML")

# === Команды для админов ===

@router.message(Command("report"))
async def cmd_report(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    stats = get_today_stats()
    if not stats:
        await message.answer("📊 За сегодня обращений не было.")
        return

    await message.answer("📊 Генерирую отчёт...")
    photos = generate_report_charts(stats)
    for photo in photos:
        await message.answer_photo(photo)

@router.message(Command("duty"))
async def cmd_duty(message: Message):
    duty_info = get_current_duty()
    if not duty_info:
        await message.answer("📅 Расписание дежурных не задано.")
    else:
        await message.answer(
            f"👤 <b>Сейчас дежурят:</b>\n\n" +
            "\n".join(f"• {name}" for name in duty_info),
            parse_mode="HTML"
        )

@router.message(Command("set_duty"))
async def cmd_set_duty(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа к этой команде.")
        return

    parts = message.text.split()[1:]
    if len(parts) < 4:
        await message.answer(
            "📋 <b>Формат команды:</b>\n\n"
            "/set_duty YYYY-MM-DD день/ночь Имя1 Имя2 ...\n\n"
            "Пример:\n"
            "/set_duty 2024-06-08 день Алексей Мария",
            parse_mode="HTML"
        )
        return

    date, shift, *names = parts
    shift = shift.lower()

    if shift not in ("день", "ночь", "day", "night"):
        await message.answer("⚠️ Смена должна быть: <b>день</b> или <b>ночь</b>")
        return

    set_duty(date, shift, names)
    shift_label = "🌅 Дневная" if shift in ("день", "day") else "🌙 Ночная"
    await message.answer(
        f"✅ Расписание обновлено!\n\n"
        f"📅 <b>{date}</b>\n"
        f"{shift_label} смена: {', '.join(names)}",
        parse_mode="HTML"
    )