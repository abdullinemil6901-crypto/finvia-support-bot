"""
Support Bot — Actions Handlers
Использует commands_config.py для масштабируемости.
Добавление новой команды = редактирование ОДНОГО файла commands_config.py
"""

import logging
import html
import re
from functools import wraps
from aiogram import Router, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import SUPPORT_CHAT_ID, TRADER_CHAT_ID
from keyboards import build_main_menu
from database import save_ticket, take_ticket, close_ticket, get_ticket
from commands_config import COMMANDS, STATE_CLASSES, get_label, needs_order_id

logger = logging.getLogger(__name__)

router = Router()


# ============================================
# HELPER: Работа с командами (чатами)
# ============================================

def get_team_info(chat) -> tuple:
    """
    Получает информацию о команде из чата.
    Returns: (chat_id, team_name)
    """
    chat_id = chat.id
    team_name = getattr(chat, 'title', None) or f"Чат {chat_id}"

    # Если title содержит только цифры — используем как есть
    # Иначе очищаем от лишних символов
    if team_name and not team_name.replace(" ", "").replace("-", "").replace("арс", "").isdigit():
        # Это нормальное название типа "309 арс"
        pass
    else:
        team_name = team_name or str(chat_id)

    return chat_id, team_name


# ============================================
# КОНСТАНТЫ ВАЛИДАЦИИ
# ============================================
MAX_ORDER_ID_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1000
MIN_ORDER_ID_LENGTH = 3
MAX_TICKETS_PER_MINUTE = 5  # Защита от спама


# ─────────────────────────────────────────────
# ФУНКЦИИ ВАЛИДАЦИИ
# ─────────────────────────────────────────────

def validate_order_id(order_id: str) -> tuple[bool, str]:
    """
    Валидация Order ID.
    Returns: (is_valid, error_message)
    """
    order_id = order_id.strip()

    if not order_id:
        return False, "Order ID не может быть пустым"

    if len(order_id) < MIN_ORDER_ID_LENGTH:
        return False, f"Order ID слишком короткий (мин. {MIN_ORDER_ID_LENGTH} симв.)"

    if len(order_id) > MAX_ORDER_ID_LENGTH:
        return False, f"Order ID слишком длинный (макс. {MAX_ORDER_ID_LENGTH} симв.)"

    # Только буквы, цифры, дефис, подчёркивание
    if not re.match(r'^[a-zA-Z0-9_\-]+$', order_id):
        return False, "Order ID содержит недопустимые символы"

    return True, ""


def validate_description(description: str) -> tuple[bool, str]:
    """
    Валидация описания проблемы.
    Returns: (is_valid, error_message)
    """
    description = description.strip()

    if not description:
        return False, "Описание не может быть пустым"

    if len(description) < 5:
        return False, "Описание слишком короткое (мин. 5 симв.)"

    if len(description) > MAX_DESCRIPTION_LENGTH:
        return False, f"Описание слишком длинное (макс. {MAX_DESCRIPTION_LENGTH} симв.)"

    return True, ""


def escape_html(text: str) -> str:
    """Безопасный escape HTML-символов."""
    return html.escape(text, quote=False)


def safe_username(username: str) -> str:
    """Безопасное имя пользователя для отображения."""
    if not username:
        return "unknown"
    safe = re.sub(r'[<>"\'`]', '', username)
    return safe[:50]


# ─────────────────────────────────────────────
# RETRY ЛОГИКА (без внешних зависимостей)
# ─────────────────────────────────────────────

async def send_with_retry(bot: Bot, chat_id: int, text: str, retries: int = 3, delay: float = 0.5, parse_mode: str = "HTML", reply_markup=None):
    """
    Отправка сообщения с retry.
    retries - количество попыток
    delay - задержка между попытками (exponential backoff)
    """
    import asyncio

    for attempt in range(retries):
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            if attempt < retries - 1:
                wait_time = delay * (2 ** attempt)  # exponential backoff
                logger.warning(f"Попытка {attempt + 1} не удалась: {e}. Retry через {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Все {retries} попыток не удались: {e}")
                return False
    return False


def build_ticket_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Взял в работу", callback_data=f"take_ticket:{ticket_id}"),
            InlineKeyboardButton(text="🏁 Завершил", callback_data=f"close_ticket:{ticket_id}")
        ]
    ])


# ─────────────────────────────────────────────
# Хендлеры для взятия/закрытия тикетов
# ─────────────────────────────────────────────

@router.callback_query(lambda c: c.data and c.data.startswith("take_ticket:"))
async def handle_take_ticket(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split(":")[1])
    ticket = get_ticket(ticket_id)
    if ticket is None:
        await callback.answer("❌ Тикет не найден.", show_alert=True)
        return
    if ticket.get("status") != "open":
        await callback.answer("⚠️ Тикет уже взят или закрыт.", show_alert=True)
        return

    support = callback.from_user
    take_ticket(ticket_id, support.username or support.full_name, support.id)
    logger.info("Ticket %s taken by %s (id=%s)", ticket_id, support.username, support.id)

    new_text = callback.message.text + f"\n\n🔧 Взял в работу: @{support.username or support.full_name}"
    await callback.message.edit_text(
        new_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏁 Завершил", callback_data=f"close_ticket:{ticket_id}")]
        ])
    )
    await callback.answer("✅ Вы взяли тикет в работу.")

    # Уведомление трейдеру в личку
    trader_id = ticket.get("trader_id")
    trader_chat_id = ticket.get("trader_chat_id")
    label = ticket.get("label") or "Обращение"
    support_name = f"@{support.username}" if support.username else support.full_name

    if trader_chat_id:
        try:
            await bot.send_message(
                chat_id=trader_chat_id,
                text=(
                    f"🔧 <b>Ваша заявка #{ticket_id} взята в работу</b>\n\n"
                    f"📋 Тип: {label}\n"
                    f"👨‍💼 Саппорт: {support_name}\n\n"
                    f"Ожидайте ответа в поддержке."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning("Не удалось уведомить трейдера %s: %s", trader_chat_id, e)


@router.callback_query(lambda c: c.data and c.data.startswith("close_ticket:"))
async def handle_close_ticket(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split(":")[1])
    ticket = get_ticket(ticket_id)
    if ticket is None:
        await callback.answer("❌ Тикет не найден.", show_alert=True)
        return
    if ticket.get("status") == "closed":
        await callback.answer("⚠️ Тикет уже закрыт.", show_alert=True)
        return

    close_ticket(ticket_id)
    support = callback.from_user
    new_text = callback.message.text + f"\n\n✅ Завершил: @{support.username or support.full_name}"
    await callback.message.edit_text(new_text, reply_markup=None)
    await callback.answer("🏁 Тикет закрыт.")

    # Уведомление трейдеру в личку
    trader_id = ticket.get("trader_id")
    trader_chat_id = ticket.get("trader_chat_id")
    trader_username = ticket.get("trader_username") or ""
    label = ticket.get("label") or "Обращение"

    if trader_chat_id:
        try:
            await bot.send_message(
                chat_id=trader_chat_id,
                text=(
                    f"✅ <b>Ваша заявка #{ticket_id} закрыта</b>\n\n"
                    f"📋 Тип: {label}\n"
                    f"👨‍💼 Саппорт: @{support.username or support.full_name}\n\n"
                    f"Если остались вопросы — создайте новое обращение."
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning("Не удалось уведомить трейдера %s: %s", trader_chat_id, e)


# ─────────────────────────────────────────────
# Хендлеры для создания тикетов (FSM)
# Генерируются автоматически из COMMANDS
# ─────────────────────────────────────────────

@router.callback_query(lambda c: c.data in COMMANDS)
async def apply_start(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории обращения."""
    cmd_key = callback.data
    config = COMMANDS[cmd_key]
    label = config["label"]
    needs_oid = config["needs_order_id"]

    await state.update_data(label=label, needs_order_id=needs_oid, cmd_key=cmd_key)

    if needs_oid:
        await callback.message.edit_text(
            f"{label}\n\n🔑 Пришлите <b>ID сделки</b>:",
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            f"{label}\n\n📝 Опишите проблему:",
            parse_mode="HTML"
        )

    # Устанавливаем состояние из сгенерированного StateGroup
    sg_class = STATE_CLASSES[cmd_key]
    await state.set_state(sg_class.waiting_for_order_id)
    await callback.answer()


async def _send_to_support(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода Order ID или описания с валидацией."""
    data = await state.get_data()
    label = data.get("label", "Обращение")
    needs_oid = data.get("needs_order_id", True)
    trader = message.from_user
    user_input = message.text.strip()

    # ─── ВАЛИДАЦИЯ ───
    if needs_oid:
        is_valid, error_msg = validate_order_id(user_input)
        if not is_valid:
            await message.answer(f"❌ {error_msg}\n\nПопробуйте ещё раз:")
            return
        order_id = user_input
    else:
        is_valid, error_msg = validate_description(user_input)
        if not is_valid:
            await message.answer(f"❌ {error_msg}\n\nПопробуйте ещё раз:")
            return
        order_id = None
    # ─────────────────

    # Безопасное имя пользователя
    trader_name_safe = safe_username(trader.full_name) if trader.full_name else ""
    username_safe = safe_username(trader.username) if trader.username else ""

    # Получаем информацию о команде из чата
    chat_id, team_name = get_team_info(message.chat)

    if needs_oid:
        text = (
            f"{escape_html(label)}\n\n"
            f"👤 Трейдер: @{escape_html(username_safe) if username_safe else escape_html(trader_name_safe)}\n"
            f"🆔 ID: {trader.id}\n"
            f"🔑 Order ID: {escape_html(order_id)}\n"
            f"📢 Команда: {escape_html(team_name)}"
        )
    else:
        text = (
            f"{escape_html(label)}\n\n"
            f"👤 Трейдер: @{escape_html(username_safe) if username_safe else escape_html(trader_name_safe)}\n"
            f"🆔 ID: {trader.id}\n"
            f"📝 Описание: {escape_html(user_input)}\n"
            f"📢 Команда: {escape_html(team_name)}"
        )

    try:
        ticket_id = save_ticket(
            trader_id=trader.id,
            trader_username=username_safe,
            trader_name=trader_name_safe,
            label=escape_html(label),
            order_id=escape_html(order_id) if order_id else None,
            team_name=team_name,
            trader_chat_id=message.chat.id
        )
        ticket_message = f"#{ticket_id} | {text}"

        # Отправка в чат поддержки с retry
        success = await send_with_retry(
            bot, SUPPORT_CHAT_ID, ticket_message,
            retries=3, delay=0.5,
            parse_mode="HTML",
            reply_markup=build_ticket_keyboard(ticket_id)
        )

        if success:
            await message.answer("✅ Запрос отправлен в поддержку!")
        else:
            logger.error("Не удалось отправить тикет после всех retry")
            await message.answer("❌ Ошибка при отправке. Попробуйте позже.")

    except Exception as e:
        logger.error("Ошибка при отправке тикета: %s", e)
        await message.answer("❌ Ошибка при отправке в поддержку. Попробуйте позже.")
    finally:
        await state.clear()


# ─────────────────────────────────────────────
# АВТОРЕГИСТРАЦИЯ всех FSM состояний
# ─────────────────────────────────────────────

for _sg in STATE_CLASSES.values():
    router.message(_sg.waiting_for_order_id)(_send_to_support)