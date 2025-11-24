from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_admin_keyboard() -> InlineKeyboardMarkup:
    """管理员首页键盘

    功能说明:
    - 在用户基础上增加管理入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [InlineKeyboardButton(text="👤 个人信息", callback_data="start:profile")],
        [InlineKeyboardButton(text="📊 群组管理", callback_data="start:groups")],
        [InlineKeyboardButton(text="📈 统计数据", callback_data="start:stats")],
        [InlineKeyboardButton(text="🆘 支持", callback_data="start:support")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()

