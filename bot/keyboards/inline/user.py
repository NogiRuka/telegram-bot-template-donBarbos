from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.core.constants import DISPLAY_MODE_SFW, DISPLAY_MODE_NSFW, DISPLAY_MODE_RANDOM
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
    buttons = MAIN_USER_BUTTONS
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2, 2)
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
        keyboard.adjust(2, 2, 2, 1)
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


def get_main_image_settings_keyboard(current_mode: str, nsfw_unlocked: bool) -> InlineKeyboardMarkup:
    """主图设置键盘

    功能说明:
    - 展示主图显示模式选项 (SFW/NSFW/随机)
    - 根据 nsfw_unlocked 状态控制 NSFW 和 随机 选项的显示
    - 选中项前添加 ✅

    输入参数:
    - current_mode: 当前模式
    - nsfw_unlocked: 是否解锁 NSFW

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    keyboard = InlineKeyboardBuilder()

    # SFW 按钮
    sfw_text = f"✅ SFW (安全)" if current_mode == DISPLAY_MODE_SFW else "SFW (安全)"
    keyboard.button(text=sfw_text, callback_data=f"{PROFILE_MAIN_IMAGE_CALLBACK_DATA}:set:{DISPLAY_MODE_SFW}")

    if nsfw_unlocked:
        # Random 按钮
        random_text = f"✅ 随机 (混合)" if current_mode == DISPLAY_MODE_RANDOM else "随机 (混合)"
        keyboard.button(text=random_text, callback_data=f"{PROFILE_MAIN_IMAGE_CALLBACK_DATA}:set:{DISPLAY_MODE_RANDOM}")
        
        # NSFW 按钮
        nsfw_text = f"✅ NSFW (限制级)" if current_mode == DISPLAY_MODE_NSFW else "NSFW (限制级)"
        keyboard.button(text=nsfw_text, callback_data=f"{PROFILE_MAIN_IMAGE_CALLBACK_DATA}:set:{DISPLAY_MODE_NSFW}")

    keyboard.adjust(1)
    
    # 返回按钮
    keyboard.row(PROFILE_BUTTON)
    
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


def get_password_input_keyboard() -> InlineKeyboardMarkup:
    """修改密码输入等待键盘

    功能说明:
    - 用户点击修改密码后展示, 仅包含取消修改按钮

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [CANCEL_PASSWORD_CHANGE_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_user_profile_keyboard() -> InlineKeyboardMarkup:
    """用户个人资料键盘
    
    功能说明:
    - 个人资料页面底部键盘，提供主图设置和返回主页按钮
    
    输入参数:
    - 无
    
    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [PROFILE_MAIN_IMAGE_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_user_tags_keyboard() -> InlineKeyboardMarkup:
    """用户标签屏蔽键盘

    功能说明:
    - 标签屏蔽页面底部键盘，提供屏蔽管理功能入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [TAGS_CUSTOM_BUTTON, TAGS_CLEAR_BUTTON],
        [BACK_TO_ACCOUNT_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2, 2)
    return keyboard.as_markup()


def get_tags_edit_keyboard() -> InlineKeyboardMarkup:
    """标签编辑取消键盘

    功能说明:
    - 标签编辑状态下使用

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [TAGS_CANCEL_EDIT_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()
