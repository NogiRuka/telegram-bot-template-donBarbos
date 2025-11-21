from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.core.config import settings


def contacts_keyboard() -> InlineKeyboardMarkup:
    """
    创建联系方式键盘

    返回:
        InlineKeyboardMarkup: 内联键盘标记
    """
    buttons = [
        [InlineKeyboardButton(text="🆘 支持", url=settings.SUPPORT_URL)],
    ]

    keyboard = InlineKeyboardBuilder(markup=buttons)

    return keyboard.as_markup()


def support_keyboard() -> InlineKeyboardMarkup:
    """
    创建支持键盘

    返回:
        InlineKeyboardMarkup: 内联键盘标记
    """
    buttons = [
        [InlineKeyboardButton(text="🆘 支持", url=settings.SUPPORT_URL)],
        [InlineKeyboardButton(text="🔙 返回", callback_data="menu")],
    ]

    keyboard = InlineKeyboardBuilder(markup=buttons)

    return keyboard.as_markup()
