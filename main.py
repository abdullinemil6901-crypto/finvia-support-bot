import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from handlers import menu, actions
from handlers.chat_events import router as chat_events_router

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(menu.router)
    dp.include_router(actions.router)
    dp.include_router(chat_events_router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
