from datetime import datetime
from io import BytesIO, StringIO
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
import csv
from keyboards import build_main_menu, build_submenu
from config.menu_config import SUBMENU_BUTTONS
from config import ADMIN_IDS
from database import (
    get_trader_tickets,
    get_support_personal_stats,
    get_all_supports,
    add_support,
    remove_support,
    get_support_by_tg_id,
    get_all_tickets
)

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
    for t in tickets[:10]:
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


@router.message(Command("duty"))
async def cmd_duty(message: Message):
    """Показать кто сейчас дежурит."""
    import schedule_manager

    duty_info = schedule_manager.get_duty_info()
    duty_names = duty_info.get("names") or []
    shift_label = duty_info.get("shift_label") or "Неизвестно"
    start_time = duty_info.get("start_time") or "—"
    end_time = duty_info.get("end_time") or "—"

    if duty_names:
        names_text = ", ".join([f"@{n}" for n in duty_names])
        text = (
            f"🌟 <b>Сейчас дежурит:</b>\n\n"
            f"{names_text}\n\n"
            f"{shift_label} смена\n"
            f"⏰ {start_time} – {end_time} МСК"
        )
    else:
        text = "👤 <b>Дежурный не назначен</b>"

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


# ─────────────────────────────────────────────
# Управление саппортами (только для админов)
# ─────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("list_supports"))
async def cmd_list_supports(message: Message):
    """Показать список всех саппортов (только админы)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Команда только для админов.")
        return

    supports = get_all_supports()
    if not supports:
        await message.answer("📋 Список саппортов пуст.")
        return

    lines = ["📋 <b>Саппорты:</b>\n"]
    for s in supports:
        username = s.get("username") or ""
        full_name = s.get("full_name") or ""
        tg_id = s.get("tg_id") or ""
        name = f"@{username}" if username else full_name or str(tg_id)
        role = s.get("role") or "support"
        lines.append(f"• {name} [{role}]")
        lines.append(f"  ID: {tg_id}\n")

    await message.answer("".join(lines), parse_mode="HTML")


@router.message(Command("add_support"))
async def cmd_add_support(message: Message):
    """Добавить саппорта: /add_support @username"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Команда только для админов.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 Использование: /add_support @username")
        return

    username = args[1].lstrip("@")
    # Добавляем с role=support по умолчанию
    add_support(0, username, "")
    await message.answer(f"✅ Саппорт @{username} добавлен.")


@router.message(Command("remove_support"))
async def cmd_remove_support(message: Message):
    """Удалить саппорта: /remove_support @username"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Команда только для админов.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("📝 Использование: /remove_support @username")
        return

    username = args[1].lstrip("@")
    await message.answer(f"✅ Саппорт @{username} удалён.")


# ─────────────────────────────────────────────
# Обработка меню
# ─────────────────────────────────────────────

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


@router.message(Command("export"))
async def cmd_export(message: Message):
    """Экспорт тикетов в CSV (только для админов)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Команда только для админов.")
        return

    tickets = get_all_tickets()
    if not tickets:
        await message.answer("📭 Нет тикетов для экспорта.")
        return

    # Генерируем CSV
    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["ID", "Trader ID", "Username", "Name", "Label", "Order ID",
                    "Status", "Taken by", "Taken at", "Closed at", "Created at"])

    # Data
    for t in tickets:
        writer.writerow([
            t[0], t[1], t[2] or "", t[3] or "", t[4] or "", t[5] or "",
            t[6] or "", t[7] or "", t[8] or "", t[9] or "", t[10] or ""
        ])

    csv_content = output.getvalue()

    # Отправляем файл
    file = BytesIO(csv_content.encode('utf-8'))
    file.name = f"tickets_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    await message.answer_document(
        file,
        caption=f"📊 Экспорт тикетов ({len(tickets)} записей)"
    )
