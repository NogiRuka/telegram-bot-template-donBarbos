from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import ADMIN_FEATURES_MAPPING, USER_FEATURES_MAPPING
from bot.keyboards.inline.buttons import (
    MAIN_OWNER_BUTTONS,
    ADMIN_LIST_BUTTON,
    BACK_TO_HOME_BUTTON,
    BACK_TO_OWNER_PANEL_BUTTON,
    OWNER_PANEL_BUTTONS,
)
from bot.keyboards.inline.constants import (
    format_with_status,
)


def get_start_owner_keyboard() -> InlineKeyboardMarkup:
    """所有者首页键盘

    功能说明:
    - 使用 menu 风格布局, 提供用户基础入口、管理员面板与所有者面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = MAIN_OWNER_BUTTONS
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(2, 2, 1, 1)
    return kb.as_markup()


def get_owner_panel_keyboard() -> InlineKeyboardMarkup:
    """所有者面板键盘

    功能说明:
    - 提供所有者面板主入口, 包含总开关、功能开关、管理员管理与返回主面板

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 面板主键盘
    """
    kb = InlineKeyboardBuilder(markup=OWNER_PANEL_BUTTONS)
    kb.adjust(1)
    return kb.as_markup()


def get_admins_panel_keyboard() -> InlineKeyboardMarkup:
    """管理员管理面板键盘

    功能说明:
    - 提供查看管理员列表与返回所有者主面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 管理员面板键盘
    """
    buttons = [
        [ADMIN_LIST_BUTTON],
        [BACK_TO_OWNER_PANEL_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(1, 2)
    return keyboard.as_markup()


def get_user_features_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """功能开关面板键盘

    功能说明:
    - 控制用户功能的开关, 使用状态 emoji (🟢/🔴) 清晰显示开启关闭
    - 底部包含返回上一级与返回主面板按钮

    输入参数:
    - features: 功能开关状态字典

    返回值:
    - InlineKeyboardMarkup: 功能开关键盘
    """

    buttons: list[list[InlineKeyboardButton]] = []

    # 1. 动态添加用户功能开关
    for short_code, (cfg_key, label) in USER_FEATURES_MAPPING.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    text=format_with_status(label, features.get(cfg_key, False)),
                    callback_data=f"owner:user_features:toggle:{short_code}",
                )
            ]
        )

    # 2. 添加返回开关
    buttons.append([BACK_TO_OWNER_PANEL_BUTTON, BACK_TO_HOME_BUTTON])

    keyboard = InlineKeyboardBuilder(markup=buttons)

    # 3. 调整布局: 机器人开关(1) -> 用户总开关(1) -> 其他开关(每行2个) -> 底部导航(每行2个)
    # USER_FEATURES_MAPPING 的前两个通常是 bot 和 all
    # 我们假设映射顺序是固定的: bot, all, ...
    # 总数 - 2 (bot, all) - 1 (bottom nav row) = remaining buttons
    # 实际上 buttons 列表长度 = mapping items + 1 (bottom row)
    
    # 按照 mappings 定义的顺序：
    # 1. bot (1)
    # 2. all (1)
    # 3. others... (2 per row)
    # 4. bottom nav (2)
    
    mapping_len = len(USER_FEATURES_MAPPING)
    # 确保至少有2个（bot, all）
    
    layout = []
    if mapping_len >= 2:
        layout.append(1) # bot
        layout.append(1) # all
        
        remaining = mapping_len - 2
        layout.extend([2] * (remaining // 2))
        if remaining % 2 != 0:
            layout.append(1)
    else:
        # Fallback if mapping is empty or weird
        layout.extend([1] * mapping_len)
        
    layout.append(2) # bottom nav

    keyboard.adjust(*layout)
    return keyboard.as_markup()


def get_admin_features_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员功能面板键盘

    功能说明:
    - 控制管理员可使用的功能权限开关, 状态使用 emoji (🟢/🔴) 显示
    - 底部包含返回上一级与返回主面板按钮

    输入参数:
    - features: 管理员功能开关映射

    返回值:
    - InlineKeyboardMarkup: 管理员功能面板键盘
    """

    buttons: list[list[InlineKeyboardButton]] = []

    # 1. 动态添加管理员功能开关
    for short_code, (cfg_key, label) in ADMIN_FEATURES_MAPPING.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    text=format_with_status(label, features.get(cfg_key, False)),
                    callback_data=f"owner:admin_features:toggle:{short_code}",
                )
            ]
        )

    # 2. 添加返回开关
    buttons.append([BACK_TO_OWNER_PANEL_BUTTON, BACK_TO_HOME_BUTTON])

    keyboard = InlineKeyboardBuilder(markup=buttons)

    # 3. 调整布局: 总开关(1) -> 其他开关(每行2个) -> 底部导航(每行2个)
    # 计算中间部分的行数
    other_features_count = len(buttons) - 3  # 减去总开关和两个底部按钮
    layout = [1]  # 总开关
    layout.extend([2] * (other_features_count // 2))
    if other_features_count % 2 == 1:
        layout.append(1)
    layout.append(2)  # 底部导航 (返回 + 主页)

    keyboard.adjust(*layout)
    return keyboard.as_markup()
