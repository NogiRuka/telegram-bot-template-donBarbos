from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_user_keyboard() -> InlineKeyboardMarkup:
    """用户首页键盘

    功能说明:
    - 提供基本功能入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [InlineKeyboardButton(text="👤 个人信息", callback_data="start:profile")],
        [InlineKeyboardButton(text="📤 消息导出", callback_data="start:export")],
        [InlineKeyboardButton(text="🆘 支持", callback_data="start:support")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()

