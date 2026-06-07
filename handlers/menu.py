from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from keyboards import build_main_menu, build_submenu
from config.menu_config import SUBMENU_BUTTONS

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Выбери тему обращения:",
        reply_markup=build_main_menu()
    )

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
