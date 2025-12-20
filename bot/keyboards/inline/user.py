from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.buttons import *


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
    - 动态集成已注册的用户功能按钮

    输入参数:
    - has_emby_account: 是否已有 Emby 账号

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    keyboard = InlineKeyboardBuilder()

    # 有 Emby 账号的情况
    if has_emby_account:
        keyboard = InlineKeyboardBuilder(markup=USER_PANEL_BUTTONS)
        keyboard.adjust(2, 2, 1, 1)
        return keyboard.as_markup()

    # 无 Emby 账号的情况
    buttons = [
        [START_REGISTER_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(1, 1)
    return keyboard.as_markup()


def get_register_input_keyboard() -> InlineKeyboardMarkup:
    """注册输入等待键盘

    功能说明:
    - 用户点击开始注册后展示, 仅包含取消注册按钮

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [CANCEL_REGISTER_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_user_info_keyboard() -> InlineKeyboardMarkup:
    """用户个人信息键盘

    功能说明:
    - 个人信息页面底部键盘，提供返回上一级和返回主页按钮

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [BACK_TO_ACCOUNT_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2)
    return keyboard.as_markup()


def get_user_profile_keyboard() -> InlineKeyboardMarkup:
    """用户个人资料键盘

    功能说明:
    - 个人资料页面底部键盘，仅提供返回主页按钮

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_user_tags_keyboard() -> InlineKeyboardMarkup:
    """用户标签屏蔽键盘

    功能说明:
    - 标签屏蔽页面底部键盘，仅提供返回主页按钮

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [BACK_TO_ACCOUNT_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2)
    return keyboard.as_markup()
