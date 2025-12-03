from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.common_buttons import (
    ACCOUNT_CENTER_BUTTON,
    ADMIN_PANEL_BUTTON,
    PROFILE_BUTTON,
)
from bot.keyboards.inline.labels import (
    BACK_TO_HOME_LABEL,
    GROUPS_LABEL,
    HITOKOTO_LABEL,
    OPEN_REGISTRATION_LABEL,
    STATS_LABEL,
)


def build_admin_home_buttons() -> list[list[InlineKeyboardButton]]:
    """管理员首页按钮集合构建

    功能说明:
    - 采用 menu 风格, 按行定义按钮, 统一通过 adjust 控制布局

    输入参数:
    - 无

    返回值:
    - list[list[InlineKeyboardButton]]: 按钮行集合
    """
    return [
        [PROFILE_BUTTON],
        [ACCOUNT_CENTER_BUTTON],
        [ADMIN_PANEL_BUTTON],
    ]


def get_start_admin_keyboard() -> InlineKeyboardMarkup:
    """管理员首页键盘

    功能说明:
    - 采用 menu 风格布局, 提供用户基础入口与管理员面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = build_admin_home_buttons()
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2, 1)
    return keyboard.as_markup()


def get_admin_panel_keyboard(perms: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员面板键盘

    功能说明:
    - 二级入口: 管理功能集合, 底部包含返回主面板

    输入参数:
    - perms: 管理员功能开关映射

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons: list[list[InlineKeyboardButton]] = []
    if perms.get("admin.features.enabled", False) and perms.get("admin.groups", False):
        buttons.append([InlineKeyboardButton(text=GROUPS_LABEL, callback_data="admin:groups")])
    if perms.get("admin.features.enabled", False) and perms.get("admin.stats", False):
        buttons.append([InlineKeyboardButton(text=STATS_LABEL, callback_data="admin:stats")])
    if perms.get("admin.features.enabled", False) and perms.get("admin.hitokoto", False):
        buttons.append([InlineKeyboardButton(text=HITOKOTO_LABEL, callback_data="admin:hitokoto")])
    if perms.get("admin.features.enabled", False) and perms.get("admin.open_registration", False):
        buttons.append([InlineKeyboardButton(text=OPEN_REGISTRATION_LABEL, callback_data="admin:open_registration")])
    buttons.append([InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back")])
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()
