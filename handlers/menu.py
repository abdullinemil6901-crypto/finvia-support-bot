from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from keyboards import build_main_menu, build_submenu
from config.menu_config import SUBMENU_BUTTONS
from database import get_trader_tickets, get_support_personal_stats

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Выбери тему обращения:",
        reply_markup=build_main_menu()
    )


@router.message(Command("my_tickets"))
async def cmd_my_tickets(message: Message):
    """Показать трейдеру его тикеты."""
    trader_id = message.from_user.id
    tickets = get_trader_tickets(trader_id)

    if not tickets:
        await message.answer("📭 У вас пока нет обращений.")
        return

    lines = []
    for t in tickets[:10]:  # Последние 10
        ticket_id, label, order_id, status, taken_by, created_at, closed_at = t[:7]
        status_icon = {"open": "🟡", "in_progress": "🔵", "closed": "✅"}.get(status, "❓")
        lines.append(f"{status_icon} #{ticket_id} | {label}")
        if order_id:
            lines.append(f"   🔑 Order: {order_id}")
        if taken_by:
            lines.append(f"   👨‍💼 Саппорт: @{taken_by}")
        lines.append(f"   📅 {created_at[:16] if created_at else ''}")
        lines.append("")

    text = "📋 <b>Ваши обращения:</b>\n\n" + "\n".join(lines)
    await message.answer(text, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показать саппорту его статистику."""
    username = message.from_user.username or message.from_user.full_name or str(message.from_user.id)
    stats = get_support_personal_stats(username)

    total = stats["total"]
    closed = stats["closed"]
    in_progress = stats["in_progress"]
    avg_time = stats["avg_seconds"]

    if total == 0:
        await message.answer("📊 У вас пока нет тикетов.")
        return

    avg_str = f"{avg_time/60:.1f} мин" if avg_time else "—"
    close_rate = f"{(closed/total*100):.0f}%" if total > 0 else "—"

    text = (
        f"📊 <b>Ваша статистика</b>\n\n"
        f"📁 Всего тикетов: {total}\n"
        f"🔵 В работе: {in_progress}\n"
        f"✅ Закрыто: {closed}\n"
        f"📈 Закрытие: {close_rate}\n"
        f"⏱ Среднее время: {avg_str}"
    )
    await message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data in SUBMENU_BUTTONS)
async def show_submenu(callback: CallbackQuery):
    await callback.message.edit_reply_markup(
        reply_markup=build_submenu(callback.data)
    )
    await callback.answer()


@router.callback_query(F.data == "back_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_reply_markup(
        reply_markup=build_main_menu()
    )
    await callback.answer()
