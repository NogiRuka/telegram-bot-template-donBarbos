from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.inline.start_admin import build_admin_home_rows
from bot.keyboards.inline.start_user import make_home_keyboard


def get_start_owner_keyboard() -> InlineKeyboardMarkup:
    """所有者首页键盘

    功能说明:
    - 复用管理员首页并追加所有者面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    rows = build_admin_home_rows()
    rows.append([InlineKeyboardButton(text="👑 所有者面板", callback_data="panel:main")])
    return make_home_keyboard(rows)

