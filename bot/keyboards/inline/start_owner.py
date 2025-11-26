from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_owner_keyboard() -> InlineKeyboardMarkup:
    """所有者首页键盘

    功能说明:
    - 复用管理员首页并追加所有者面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [InlineKeyboardButton(text="👤 个人信息", callback_data="start:profile")],
        [InlineKeyboardButton(text="🧾 账号中心", callback_data="start:account")],
        [InlineKeyboardButton(text="🛡️ 管理员面板", callback_data="admin:panel")],
        [InlineKeyboardButton(text="👑 所有者面板", callback_data="panel:main")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()

