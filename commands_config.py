"""
Support Bot — Конфигурация команд
Все команды в одном месте — масштабируемо для 20+ команд.

Добавление новой команды:
1. Добавить entry в COMMANDS dict (здесь)
2. Готово — FSM states и handlers генерируются автоматически
"""

from aiogram.fsm.state import State, StatesGroup


# ─────────────────────────────────────────────
# ОПРЕДЕЛЕНИЕ КОМАНД
# ─────────────────────────────────────────────
# key: callback_data для кнопки
# needs_order_id: запрашивать ли Order ID у трейдера
# label: текст для отображения

COMMANDS = {
    "apply_cancel_payout": {
        "label": "🚫 Отмена выплаты",
        "needs_order_id": True,
    },
    "apply_payout_not_visible": {
        "label": "👁 Выплата не видна на токене",
        "needs_order_id": True,
    },
    "apply_extend_time": {
        "label": "⏱ Продлить время ордера",
        "needs_order_id": True,
    },
    "apply_no_receipt": {
        "label": "🧾 Нет чека / не прогрузился",
        "needs_order_id": True,
    },
    "apply_wrong_receipt": {
        "label": "📎 Неверный чек прикреплён",
        "needs_order_id": True,
    },
    "apply_wrong_cvu": {
        "label": "❌ Неверный CVU / не наш реквизит",
        "needs_order_id": True,
    },
    "apply_wrong_requisite": {
        "label": "🚷 Не наш реквизит",
        "needs_order_id": True,
    },
    "apply_verify_requisites": {
        "label": "⚙️ Верификация реквизитов",
        "needs_order_id": True,
    },
    "apply_tech_issue": {
        "label": "⚙️ Технический сбой",
        "needs_order_id": True,
    },
    "apply_token_issue": {
        "label": "🔧 Токен не работает",
        "needs_order_id": False,
    },
    "apply_appeal": {
        "label": "⚖️ Апелляция",
        "needs_order_id": True,
    },
    "apply_no_traffic": {
        "label": "📡 Нет трафика / ордеров",
        "needs_order_id": False,
    },
    "apply_increase_limits": {
        "label": "📈 Увеличить лимиты",
        "needs_order_id": True,
    },
}


# ─────────────────────────────────────────────
# АВТОГЕНЕРАЦИЯ FSM STATES
# ─────────────────────────────────────────────

def generate_state_classes():
    """
    Генерирует StateGroup классы динамически на основе COMMANDS.
    Не нужно вручную добавлять классы в states.py!
    """
    state_classes = {}
    for key in COMMANDS:
        # Создаём уникальное имя класса
        class_name = "".join(
            part.capitalize()
            for part in key.replace("apply_", "").replace("_", " ").split()
        ) + "SG"

        # Создаём класс StateGroup
        state_classes[key] = type(
            class_name,
            (StatesGroup,),
            {"waiting_for_order_id": State()}
        )

    return state_classes


# Генерируем все StateGroup классы
STATE_CLASSES = generate_state_classes()


# ─────────────────────────────────────────────
# ЭКСПОРТ ДЛЯ СОВМЕСТИМОСТИ
# ─────────────────────────────────────────────

# Экспортируем все сгенерированные StateGroup классы
for key, cls in STATE_CLASSES.items():
    globals()[cls.__name__] = cls


# Список всех StateGroup для регистрации в роутере
ALL_STATE_CLASSES = list(STATE_CLASSES.values())


# ─────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────

def get_label(key: str) -> str:
    """Получить label по ключу команды."""
    return COMMANDS.get(key, {}).get("label", "Неизвестно")


def needs_order_id(key: str) -> bool:
    """Проверить, нужен ли Order ID для команды."""
    return COMMANDS.get(key, {}).get("needs_order_id", True)


def get_all_commands() -> list:
    """Получить список всех команд (ключей)."""
    return list(COMMANDS.keys())
