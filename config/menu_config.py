"""
Support Bot — Menu Configuration
Использует команды из commands_config.py для синхронизации.
"""

from commands_config import COMMANDS

# Основное меню — категории
MAIN_MENU_BUTTONS = [
    {"text": "💸 Выплаты",               "callback": "cat_payouts"},
    {"text": "🧾 Чеки / документы",       "callback": "cat_receipts"},
    {"text": "❌ Реквизиты / CVU",        "callback": "cat_requisites"},
    {"text": "⚙️ Технические проблемы",   "callback": "cat_tech"},
    {"text": "📡 Трафик / лимиты",        "callback": "cat_traffic"},
]

# Подменю — маппинг категория → список команд
# Автоматически генерируется из COMMANDS
SUBMENU_BUTTONS = {
    "cat_payouts": [
        {"text": "🚫 Отмена выплаты",            "callback": "apply_cancel_payout"},
        {"text": "👁 Выплата не видна на токене", "callback": "apply_payout_not_visible"},
        {"text": "⏱ Продлить время ордера",       "callback": "apply_extend_time"},
    ],
    "cat_receipts": [
        {"text": "🧾 Нет чека / не прогрузился",  "callback": "apply_no_receipt"},
        {"text": "📎 Неверный чек прикреплён",     "callback": "apply_wrong_receipt"},
    ],
    "cat_requisites": [
        {"text": "❌ Неверный CVU",               "callback": "apply_wrong_cvu"},
        {"text": "🚷 Не наш реквизит",            "callback": "apply_wrong_requisite"},
        {"text": "✅ Верификация реквизитов",      "callback": "apply_verify_requisites"},
    ],
    "cat_tech": [
        {"text": "⚙️ Технический сбой",           "callback": "apply_tech_issue"},
        {"text": "🔧 Токен не работает",           "callback": "apply_token_issue"},
        {"text": "⚖️ Апелляция",                  "callback": "apply_appeal"},
    ],
    "cat_traffic": [
        {"text": "📡 Нет трафика / ордеров",       "callback": "apply_no_traffic"},
        {"text": "📈 Увеличить лимиты",            "callback": "apply_increase_limits"},
    ],
}


# ─────────────────────────────────────────────
# УТИЛИТЫ для работы с меню
# ─────────────────────────────────────────────

def get_all_callbacks() -> list:
    """Получить все callback_data из меню."""
    callbacks = []
    for buttons in SUBMENU_BUTTONS.values():
        for btn in buttons:
            callbacks.append(btn["callback"])
    return callbacks


def get_button_text(callback_data: str) -> str:
    """Получить текст кнопки по callback_data."""
    for buttons in SUBMENU_BUTTONS.values():
        for btn in buttons:
            if btn["callback"] == callback_data:
                return btn["text"]
    return callback_data


def get_category_by_callback(callback_data: str) -> str:
    """Получить категорию по callback_data."""
    for category, buttons in SUBMENU_BUTTONS.items():
        for btn in buttons:
            if btn["callback"] == callback_data:
                return category
    return None