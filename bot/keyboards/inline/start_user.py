from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.common_buttons import (
    ACCOUNT_CENTER_BUTTON,
    BACK_TO_HOME_BUTTON,
    PROFILE_BUTTON,
    START_REGISTER_BUTTON,
    USER_DEVICES_BUTTON,
    USER_INFO_BUTTON,
    USER_LINES_BUTTON,
    USER_PASSWORD_BUTTON,
)


def get_start_user_keyboard() -> InlineKeyboardMarkup:
    """用户首页键盘

    功能说明:
    - 提供一级入口: 个人信息与账号中心, 使用 menu 风格布局

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [PROFILE_BUTTON],
        [ACCOUNT_CENTER_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2)
    return keyboard.as_markup()


def get_account_center_keyboard(has_emby_account: bool) -> InlineKeyboardMarkup:
    """账号中心键盘

    功能说明:
    - 若已有 Emby 账号: 展示账号信息、线路信息、设备管理、修改密码与返回主面板, 使用 menu 风格布局
    - 若尚无 Emby 账号: 展示开始注册与返回主面板, 使用 menu 风格布局

    输入参数:
    - has_emby_account: 是否已有 Emby 账号

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    if has_emby_account:
        buttons = [
            [USER_INFO_BUTTON],
            [USER_LINES_BUTTON],
            [USER_DEVICES_BUTTON],
            [USER_PASSWORD_BUTTON],
            [BACK_TO_HOME_BUTTON],
        ]
        keyboard = InlineKeyboardBuilder(markup=buttons)
        keyboard.adjust(2, 2, 1)
        return keyboard.as_markup()
    buttons = [
        [START_REGISTER_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(1, 1)
    return keyboard.as_markup()
