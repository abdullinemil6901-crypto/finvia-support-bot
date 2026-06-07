MAIN_MENU_BUTTONS = [
    {"text": "💸 Выплаты",               "callback": "cat_payouts"},
    {"text": "🧾 Чеки / документы",       "callback": "cat_receipts"},
    {"text": "❌ Реквизиты / CVU",        "callback": "cat_requisites"},
    {"text": "⚙️ Технические проблемы",   "callback": "cat_tech"},
    {"text": "📡 Трафик / лимиты",        "callback": "cat_traffic"},
]

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
