from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import SUPPORT_CHAT_ID, ADMIN_IDS
from db import log_event, get_today_stats
from charts import generate_report_charts
from schedule_manager import get_current_duty

router = Router()

TYPE_LABELS = {
    "cancel_payment": "Отмена платежа",
    "wrong_cvu": "Неверный CVU",
    "no_receipt": "Нет чека",
    "other": "Другое",
}

class OtherForm(StatesGroup):
    waiting_description = State()
    waiting_amount = State()

def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена платежа", callback_data="type_cancel_payment")],
        [InlineKeyboardButton(text="🔢 Неверный CVU", callback_data="type_wrong_cvu")],
        [InlineKeyboardButton(text="🧾 Нет чека", callback_data="type_no_receipt")],
        [InlineKeyboardButton(text="📝 Другое", callback_data="type_other")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_form")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в поддержку Finvia!\n\nВыберите тип обращения:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "type_cancel_payment")
async def cb_cancel_payment(callback: CallbackQuery, bot: Bot):
    log_event("cancel_payment", callback.from_user.id, callback.from_user.username)
    await callback.message.answer("✅ Обращение \"Отмена платежа\" зафиксировано. Ожидайте ответа от поддержки.")
    await notify_support(bot, "cancel_payment", callback.from_user.id, callback.from_user.username)
    await callback.answer()

@router.callback_query(F.data == "type_wrong_cvu")
async def cb_wrong_cvu(callback: CallbackQuery, bot: Bot):
    log_event("wrong_cvu", callback.from_user.id, callback.from_user.username)
    await callback.message.answer("✅ Обращение \"Неверный CVU\" зафиксировано. Ожидайте ответа от поддержки.")
    await notify_support(bot, "wrong_cvu", callback.from_user.id, callback.from_user.username)
    await callback.answer()

@router.callback_query(F.data == "type_no_receipt")
async def cb_no_receipt(callback: CallbackQuery, bot: Bot):
    log_event("no_receipt", callback.from_user.id, callback.from_user.username)
    await callback.message.answer("✅ Обращение \"Нет чека\" зафиксировано. Ожидайте ответа от поддержки.")
    await notify_support(bot, "no_receipt", callback.from_user.id, callback.from_user.username)
    await callback.answer()

@router.callback_query(F.data == "type_other")
async def cb_other(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OtherForm.waiting_description)
    await callback.message.answer(
        "📝 Опишите вашу проблему:",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.message(OtherForm.waiting_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(OtherForm.waiting_amount)
    await message.answer(
        "💰 Укажите сумму (или напишите \"нет\", если не применимо):",
        reply_markup=get_cancel_keyboard()
    )

@router.message(OtherForm.waiting_amount)
async def process_amount(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    description = data.get("description", "")
    amount = message.text
    log_event("other", message.from_user.id, message.from_user.username)
    uname = f"@{message.from_user.username}" if message.from_user.username else f"id:{message.from_user.id}"
    text = (
        f"📥 <b>Новая заявка</b>\n\n"
        f"📌 Тип: <b>Другое</b>\n"
        f"👤 Трейдер: {uname}\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"📝 Описание: {description}\n"
        f"💰 Сумма: {amount}"
    )
    await bot.send_message(SUPPORT_CHAT_ID, text, parse_mode="HTML")
    await message.answer("✅ Ваше обращение зафиксировано. Ожидайте ответа от поддержки.")
    await state.clear()

@router.callback_query(F.data == "cancel_form")
async def cb_cancel_form(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("❌ Действие отменено.", reply_markup=get_main_keyboard())
    await callback.answer()

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
