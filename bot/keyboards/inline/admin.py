from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import (
    ADMIN_PANEL_VISIBLE_FEATURES,
    ADMIN_FEATURES_MAPPING,
    KEY_ADMIN_FEATURES_ENABLED,
)
from bot.keyboards.inline.buttons import (
    MAIN_ADMIN_BUTTONS,
    BACK_TO_ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
    NOTIFY_SEND_BUTTON
)
from bot.keyboards.inline.constants import (
    NOTIFY_COMPLETE_CALLBACK_DATA,
    NOTIFY_COMPLETE_LABEL,
    NOTIFY_PREVIEW_CALLBACK_DATA,
    NOTIFY_PREVIEW_LABEL,
)


def get_start_admin_keyboard() -> InlineKeyboardMarkup:
    """管理员首页键盘

    功能说明:
    - 采用 menu 风格布局, 提供用户基础入口与管理员面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = MAIN_ADMIN_BUTTONS
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()


def get_admin_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员面板键盘

    功能说明:
    - 二级入口: 管理功能集合, 底部包含返回主面板

    输入参数:
    - perms: 管理员功能开关映射

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons: list[list[InlineKeyboardButton]] = []
    master_enabled = features.get(KEY_ADMIN_FEATURES_ENABLED, False)

    for short_code in ADMIN_PANEL_VISIBLE_FEATURES:
        if short_code not in ADMIN_FEATURES_MAPPING:
            continue

        config_key, label = ADMIN_FEATURES_MAPPING[short_code]
        if master_enabled and features.get(config_key, False):
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"admin:{short_code}")])

    buttons.append([BACK_TO_HOME_BUTTON])
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


def get_notification_panel_keyboard(pending_completion: int, pending_review: int) -> InlineKeyboardMarkup:
    """获取上新通知管理面板键盘

    功能说明:
    - 包含 [上新补全]、[上新预览]、[一键通知] 三个主要功能按钮
    - 底部包含 [返回上一级] (到管理员面板) 和 [返回主页]

    输入参数:
    - pending_completion: 待补全数量
    - pending_review: 待审核数量

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{NOTIFY_COMPLETE_LABEL} ({pending_completion})",
                callback_data=NOTIFY_COMPLETE_CALLBACK_DATA,
            ),
            InlineKeyboardButton(
                text=f"{NOTIFY_PREVIEW_LABEL} ({pending_review})",
                callback_data=NOTIFY_PREVIEW_CALLBACK_DATA,
            ),
        ],
        [NOTIFY_SEND_BUTTON],
        [BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()
