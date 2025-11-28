from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.start_user import build_user_home_rows, make_home_keyboard
from bot.keyboards.inline.labels import (
    ADMIN_PANEL_LABEL,
    GROUPS_LABEL,
    STATS_LABEL,
    HITOKOTO_LABEL,
    OPEN_REGISTRATION_LABEL,
    BACK_TO_HOME_LABEL,
)


def build_admin_home_rows() -> list[list[InlineKeyboardButton]]:
    """管理员首页行构建

    功能说明:
    - 在用户基础首页按钮行上追加管理员面板入口

    输入参数:
    - 无

    返回值:
    - list[list[InlineKeyboardButton]]: 按钮行集合
    """
    rows = build_user_home_rows()
    rows.append([InlineKeyboardButton(text=ADMIN_PANEL_LABEL, callback_data="admin:panel")])
    return rows


def get_start_admin_keyboard() -> InlineKeyboardMarkup:
    """管理员首页键盘

    功能说明:
    - 复用用户首页并追加管理员面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    return make_home_keyboard(build_admin_home_rows())


def get_admin_panel_keyboard(perms: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员面板键盘

    功能说明:
    - 二级入口: 管理功能集合, 底部包含返回主面板

    输入参数:
    - perms: 管理员功能开关映射

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    builder = InlineKeyboardBuilder()
    if perms.get("admin.features.enabled", False) and perms.get("admin.groups", False):
        builder.row(InlineKeyboardButton(text=GROUPS_LABEL, callback_data="admin:groups"))
    if perms.get("admin.features.enabled", False) and perms.get("admin.stats", False):
        builder.row(InlineKeyboardButton(text=STATS_LABEL, callback_data="admin:stats"))
    if perms.get("admin.features.enabled", False) and perms.get("admin.hitokoto", False):
        builder.row(InlineKeyboardButton(text=HITOKOTO_LABEL, callback_data="admin:hitokoto"))
    if perms.get("admin.features.enabled", False) and perms.get("admin.open_registration", False):
        builder.row(InlineKeyboardButton(text=OPEN_REGISTRATION_LABEL, callback_data="admin:open_registration"))
    builder.row(InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back"))
    return builder.as_markup()
