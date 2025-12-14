from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.common_buttons import (
    ACCOUNT_CENTER_BUTTON,
    ADMIN_PANEL_BUTTON,
    PROFILE_BUTTON,
)
from bot.keyboards.inline.labels import (
    BACK_TO_HOME_LABEL,
)
from bot.services.config_service import (
    ADMIN_PANEL_VISIBLE_FEATURES,
    ADMIN_PERMISSIONS_MAPPING,
    KEY_ADMIN_FEATURES_ENABLED,
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
    master_enabled = perms.get(KEY_ADMIN_FEATURES_ENABLED, False)

    for short_code in ADMIN_PANEL_VISIBLE_FEATURES:
        if short_code not in ADMIN_PERMISSIONS_MAPPING:
            continue
            
        config_key, label = ADMIN_PERMISSIONS_MAPPING[short_code]
        if master_enabled and perms.get(config_key, False):
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"admin:{short_code}")])

    buttons.append([InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back")])
    keyboard = InlineKeyboardBuilder(markup=buttons)
    
    # 动态调整布局: 每行2个, 最后1个返回键单独一行
    # 如果按钮数量(不含返回键)是奇数, 则最后一个功能键单独一行
    count = len(buttons) - 1
    layout = [2] * (count // 2)
    if count % 2 == 1:
        layout.append(1)
    layout.append(1)  # 返回键
    
    keyboard.adjust(*layout)
    return keyboard.as_markup()
