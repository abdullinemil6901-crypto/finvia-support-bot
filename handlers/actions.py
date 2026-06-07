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
SUPPORT_CHAT_ID = -5160275115
from keyboards import build_main_menu
from database import save_ticket

router = Router()

# Категории БЕЗ Order ID (трафик, токен)
NO_ORDER_ID_KEYS = {"apply_no_traffic", "apply_token_issue"}

APPLY_HANDLERS = {
    "apply_cancel_payout":       (CancelPayoutSG,       "🚫 Отмена выплаты",                True),
    "apply_payout_not_visible":  (PayoutNotVisibleSG,   "👁 Выплата не видна на токене",    True),
    "apply_extend_time":         (ExtendTimeSG,         "⏱ Продлить время ордера",          True),
    "apply_no_receipt":          (NoReceiptSG,          "🧾 Нет чека / не прогрузился",     True),
    "apply_wrong_receipt":       (WrongReceiptSG,       "📎 Неверный чек прикреплён",       True),
    "apply_wrong_cvu":           (WrongCVUSG,           "❌ Неверный CVU / не наш реквизит", True),
    "apply_wrong_requisite":     (WrongRequisiteSG,     "🚷 Не наш реквизит",               True),
    "apply_verify_requisites":   (VerifyRequisitesSG,   "⚙️ Техническая проблема / верификация реквизитов", True),
    "apply_tech_issue":          (TechIssueSG,          "⚙️ Технический сбой",              True),
    "apply_token_issue":         (TokenIssueSG,         "🔧 Токен не работает",             False),
    "apply_appeal":              (AppealSG,             "⚖️ Апелляция",                     True),
    "apply_no_traffic":          (NoTrafficSG,          "📡 Нет трафика / ордеров",         False),
    "apply_increase_limits":     (IncreaseLimitsSG,     "📈 Увеличить лимиты",              True),
}


@router.callback_query(lambda c: c.data in APPLY_HANDLERS)
async def apply_start(callback: CallbackQuery, state: FSMContext):
    sg_class, label, needs_order_id = APPLY_HANDLERS[callback.data]
    await state.update_data(label=label, needs_order_id=needs_order_id)
    if needs_order_id:
        await callback.message.edit_text(
            f"{label}\n\n🔑 Пришлите <b>ID сделки</b>:",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"{label}\n\n📝 Опишите проблему:",
            parse_mode="HTML"
        )
    await state.set_state(sg_class.waiting_for_order_id)
    await callback.answer()


async def _send_to_support(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    label = data.get("label", "Обращение")
    needs_order_id = data.get("needs_order_id", True)
    trader = message.from_user
    user_input = message.text.strip()

    if needs_order_id:
        order_id = user_input
        text = (
            f"{label}\n\n"
            f"👤 Трейдер: @{trader.username or trader.full_name}\n"
            f"🆔 ID: {trader.id}\n"
            f"🔑 Order ID: {order_id}"
        )
    else:
        order_id = None
        text = (
            f"{label}\n\n"
            f"👤 Трейдер: @{trader.username or trader.full_name}\n"
            f"🆔 ID: {trader.id}\n"
            f"📝 Описание: {user_input}"
        )

    try:
        ticket_id = save_ticket(
            trader_id=trader.id,
            trader_username=trader.username or "",
            trader_name=trader.full_name or "",
            label=label,
            order_id=order_id
        )
        await bot.send_message(
            chat_id=SUPPORT_CHAT_ID,
            text=f"#{ticket_id} | {text}",
            parse_mode="HTML"
        )
        await message.answer("✅ Запрос отправлен в поддержку!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке в поддержку: {e}")
    finally:
        await state.clear()


for _sg in [
    CancelPayoutSG, PayoutNotVisibleSG, ExtendTimeSG,
    NoReceiptSG, WrongReceiptSG, WrongCVUSG, WrongRequisiteSG,
    VerifyRequisitesSG, TechIssueSG, TokenIssueSG, AppealSG,
    NoTrafficSG, IncreaseLimitsSG
]:
    router.message(_sg.waiting_for_order_id)(_send_to_support)
