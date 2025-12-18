from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.features import get_all_user_feature_buttons
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
from bot.keyboards.inline.labels import BACK_LABEL, CANCEL_REGISTER_LABEL


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

    if has_emby_account:
        # 1. 添加核心功能按钮
        keyboard.add(USER_INFO_BUTTON)
        keyboard.add(USER_LINES_BUTTON)
        keyboard.add(USER_DEVICES_BUTTON)
        keyboard.add(USER_PASSWORD_BUTTON)
        
        # 2. 添加动态注册的功能按钮
        dynamic_buttons = get_all_user_feature_buttons()
        for btn in dynamic_buttons:
            keyboard.add(btn)
            
        # 3. 添加返回按钮
        keyboard.add(BACK_TO_HOME_BUTTON)
        
        # 4. 调整布局
        # 计算除了返回按钮之外的按钮数量
        total_buttons = 4 + len(dynamic_buttons)
        
        # 布局策略: 核心功能和动态功能都按每行2个排列
        layout = [2] * (total_buttons // 2)
        if total_buttons % 2 == 1:
            layout.append(1)
        
        # 最后一行是返回按钮
        layout.append(1)
        
        keyboard.adjust(*layout)
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
        [InlineKeyboardButton(text=CANCEL_REGISTER_LABEL, callback_data="user:cancel_register")],
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
        [InlineKeyboardButton(text=BACK_LABEL, callback_data="user:account")],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(1, 1)
    return keyboard.as_markup()
