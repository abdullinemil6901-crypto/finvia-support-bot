from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.menu_config import MAIN_MENU_BUTTONS, SUBMENU_BUTTONS

def build_main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback"])]
        for btn in MAIN_MENU_BUTTONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_submenu(category: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback"])]
        for btn in SUBMENU_BUTTONS.get(category, [])
    ]
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
