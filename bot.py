# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚀  bot.py — Точка входа. Запускает polling бота.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import init_db
from handlers import router

# 📋 Логи в консоль
logging.basicConfig(level=logging.INFO)


async def main():
    # 🗄️ Инициализация базы данных
    init_db()

    # 🤖 Создаём бота
    bot = Bot(token=BOT_TOKEN)

    # 🚦 Диспетчер с роутером
    dp = Dispatcher()
    dp.include_router(router)

    # 📡 Запуск
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
