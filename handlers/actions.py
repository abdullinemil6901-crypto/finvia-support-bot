from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from aiogram.filters import Command
from states import (
    CancelPayoutSG, PayoutNotVisibleSG, ExtendTimeSG,
    NoReceiptSG, WrongReceiptSG, WrongCVUSG, WrongRequisiteSG,
    VerifyRequisitesSG, TechIssueSG, TokenIssueSG, AppealSG,
    NoTrafficSG, IncreaseLimitsSG
)
from config import SUPPORT_CHAT_ID
from keyboards import build_main_menu

router = Router()

APPLY_HANDLERS = {
    "apply_cancel_payout":       (CancelPayoutSG,       "🚫 Отмена выплаты"),
    "apply_payout_not_visible":  (PayoutNotVisibleSG,   "👁 Выплата не видна на токене"),
    "apply_extend_time":         (ExtendTimeSG,         "⏱ Продлить время ордера"),
    "apply_no_receipt":          (NoReceiptSG,          "🧾 Нет чека / не прогрузился"),
    "apply_wrong_receipt":       (WrongReceiptSG,       "📎 Неверный чек прикреплён"),
    "apply_wrong_cvu":           (WrongCVUSG,           "❌ Неверный CVU"),
    "apply_wrong_requisite":     (WrongRequisiteSG,     "🚷 Не наш реквизит"),
    "apply_verify_requisites":   (VerifyRequisitesSG,   "✅ Верификация реквизитов"),
    "apply_tech_issue":          (TechIssueSG,          "⚙️ Технический сбой"),
    "apply_token_issue":         (TokenIssueSG,         "🔧 Токен не работает"),
    "apply_appeal":              (AppealSG,             "⚖️ Апелляция"),
    "apply_no_traffic":          (NoTrafficSG,          "📡 Нет трафика / ордеров"),
    "apply_increase_limits":     (IncreaseLimitsSG,     "📈 Увеличить лимиты"),
}

@router.callback_query(lambda c: c.data in APPLY_HANDLERS)
async def apply_start(callback: CallbackQuery, state: FSMContext):
    sg_class, label = APPLY_HANDLERS[callback.data]
    await state.update_data(label=label)
    await callback.message.edit_text(
        f"{label}\n\n🔑 Пришлите <b>ID сделки</b>:",
        parse_mode="HTML"
    )
    await state.set_state(sg_class.waiting_for_order_id)
    await callback.answer()

async def _send_to_support(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    label = data.get("label", "Обращение")
    trader = message.from_user
    order_id = message.text.strip()

    text = (
        f"{label}\n\n"
        f"👤 Трейдер: @{trader.username or trader.full_name}\n"
        f"🆔 ID: {trader.id}\n"
        f"🔑 Order ID: {order_id}"
    )

    await bot.send_message(chat_id=SUPPORT_CHAT_ID, text=text, parse_mode="HTML")
    await message.answer("✅ Запрос отправлен в поддержку!", reply_markup=build_main_menu())
    await state.clear()

for _sg in [
    CancelPayoutSG, PayoutNotVisibleSG, ExtendTimeSG,
    NoReceiptSG, WrongReceiptSG, WrongCVUSG, WrongRequisiteSG,
    VerifyRequisitesSG, TechIssueSG, TokenIssueSG, AppealSG,
    NoTrafficSG, IncreaseLimitsSG
]:
    router.message(_sg.waiting_for_order_id)(_send_to_support)
