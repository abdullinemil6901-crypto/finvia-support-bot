import asyncio
import logging
import signal
import threading
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db
from handlers import menu, actions
from handlers.chat_events import router as chat_events_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_api():
    """Запускает FastAPI в отдельном потоке."""
    import uvicorn
    from api import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


async def main():
    init_db()
    logger.info("База данных инициализирована")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(menu.router)
    dp.include_router(actions.router)
    dp.include_router(chat_events_router)

    # Запускаем API в отдельном потоке
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    logger.info("API запущен на порту 8000")

    loop = asyncio.get_running_loop()

    stop_event = asyncio.Event()

    def _shutdown():
        logger.info("Получен сигнал завершения, останавливаем бота...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            pass

    logger.info("Бот запущен, начинаем polling")
    polling_task = asyncio.create_task(
        dp.start_polling(bot, handle_signals=False)
    )

    await stop_event.wait()
    polling_task.cancel()
    try:
        await polling_task
    except asyncio.CancelledError:
        pass

    await bot.session.close()
    logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
