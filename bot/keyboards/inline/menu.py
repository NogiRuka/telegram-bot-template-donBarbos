from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_keyboard() -> InlineKeyboardMarkup:
    """
    创建主菜单键盘

    返回:
        InlineKeyboardMarkup: 内联键盘标记
    """
    buttons = [
        [InlineKeyboardButton(text="💰 钱包", callback_data="wallet")],
        [InlineKeyboardButton(text="⭐ 高级功能", callback_data="premium")],
        [InlineKeyboardButton(text="ℹ️ 信息", callback_data="info")],
        [InlineKeyboardButton(text="🆘 支持", callback_data="support")],
    ]

    keyboard = InlineKeyboardBuilder(markup=buttons)

    keyboard.adjust(1, 1, 2)

    return keyboard.as_markup()
