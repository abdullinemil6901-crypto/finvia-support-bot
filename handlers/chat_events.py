"""
handlers/chat_events.py — обработка событий чата.
Автоматически собирает chat_id при добавлении бота в чат.

NOTE: Использует Supabase напрямую. SQLite не поддерживается
для таблицы chats (только для локальной разработки без Supabase).
"""
import logging
from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated

logger = logging.getLogger(__name__)

router = Router()


@router.my_chat_member()
async def on_bot_added_to_chat(update: ChatMemberUpdated, bot: Bot):
    """
    Срабатывает когда бота добавляют/удаляют из чата.
    """
    chat = update.chat
    user = update.from_user

    # Интересно только для групп/супергрупп
    if chat.type not in ("group", "supergroup"):
        return

    new_status = update.new_chat_member.status
    old_status = update.old_chat_member.status

    # Бота добавили
    if new_status in ("member", "administrator", "creator") and old_status in ("kicked", "left"):
        logger.info("Бот добавлен в чат: %s (%s) пользователем @%s",
                    chat.title, chat.id, user.username)

        from supabase_client import save_chat
        team_name = chat.title or f"Чат {chat.id}"
        try:
            save_chat(chat.id, team_name)
            logger.info("Чат сохранён: %s", team_name)
        except Exception as e:
            logger.error("Ошибка сохранения чата: %s", e)

    # Бота удалили
    elif new_status in ("kicked", "left"):
        logger.info("Бот удалён из чата: %s (%s)", chat.title, chat.id)

        from supabase_client import deactivate_chat
        try:
            deactivate_chat(chat.id)
            logger.info("Чат деактивирован: %s", chat.id)
        except Exception as e:
            logger.error("Ошибка деактивации чата: %s", e)