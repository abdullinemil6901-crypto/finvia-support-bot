# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⚙️  config.py — Настройки бота. Токен, админы, типы.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 🔑 Токен от BotFather (читается из переменной окружения для Railway)
import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "8989311610:AAFuc6bLGjJKHzSD4cKJgJrRd32LWu0VGyk")
SUPPORT_CHAT_ID = int(os.getenv("SUPPORT_CHAT_ID", "5160275115"))

# 👑 Список Telegram ID администраторов
ADMIN_IDS = [8480479055]

# 📋 Типы обращений: команда → название
TYPE_LABELS = {
    "cancel_payment": "Отмена платежа",
    "wrong_cvu": "Неверный CVU",
    "no_receipt": "Нет чека",
    "other": "Другое",
}
