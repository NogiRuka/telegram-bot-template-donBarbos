from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import ADMIN_PERMISSIONS_MAPPING, USER_FEATURES_MAPPING
from bot.keyboards.inline.buttons import (
    ACCOUNT_CENTER_BUTTON,
    ADMIN_LIST_BUTTON,
    ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
    BACK_TO_OWNER_PANEL_BUTTON,
    OWNER_PANEL_BUTTON,
    OWNER_PANEL_BUTTONS,
    PROFILE_BUTTON,
)
from bot.keyboards.inline.constants import (
    ADMIN_PERMS_TOGGLE_FEATURES_CALLBACK_DATA,
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
    buttons = [
        [PROFILE_BUTTON],
        [ACCOUNT_CENTER_BUTTON],
        [ADMIN_PANEL_BUTTON],
        [OWNER_PANEL_BUTTON],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(2, 1, 1)
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


def get_features_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
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

    # 使用映射配置动态生成按钮, 参考管理员配置实现
    for short_code, (cfg_key, label) in USER_FEATURES_MAPPING.items():
        is_enabled = features.get(cfg_key, False)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=format_with_status(label, is_enabled), callback_data=f"owner:features:toggle:{short_code}"
                )
            ]
        )

    # 添加底部导航按钮
    buttons.extend(
        [
            [BACK_TO_OWNER_PANEL_BUTTON],
            [BACK_TO_HOME_BUTTON],
        ]
    )

    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(1, 1, 2, 2, 2, 2, 2)
    return keyboard.as_markup()


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


def get_admin_perms_panel_keyboard(perms: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员权限面板键盘

    功能说明:
    - 控制管理员可使用的功能权限开关, 状态使用 emoji (🟢/🔴) 显示
    - 底部包含返回上一级与返回主面板按钮

    输入参数:
    - perms: 管理员权限映射

    返回值:
    - InlineKeyboardMarkup: 管理员权限面板键盘
    """

    buttons: list[list[InlineKeyboardButton]] = []

    # 1. 优先添加管理员总开关
    if "features" in ADMIN_PERMISSIONS_MAPPING:
        cfg_key, label = ADMIN_PERMISSIONS_MAPPING["features"]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=format_with_status(label, perms.get(cfg_key, False)),
                    callback_data=ADMIN_PERMS_TOGGLE_FEATURES_CALLBACK_DATA,
                )
            ]
        )

    # 2. 动态添加其他权限开关
    for short_code, (cfg_key, label) in ADMIN_PERMISSIONS_MAPPING.items():
        if short_code == "features":
            continue
        buttons.append(
            [
                InlineKeyboardButton(
                    text=format_with_status(label, perms.get(cfg_key, False)),
                    callback_data=f"owner:admin_perms:toggle:{short_code}",
                )
            ]
        )

    buttons.append([BACK_TO_OWNER_PANEL_BUTTON])
    buttons.append([BACK_TO_HOME_BUTTON])

    keyboard = InlineKeyboardBuilder(markup=buttons)
    # 调整布局: 总开关(1) -> 其他开关(每行2个) -> 底部导航(每行2个)
    # 计算中间部分的行数
    other_perms_count = len(buttons) - 3  # 减去总开关和两个底部按钮
    layout = [1]  # 总开关
    layout.extend([2] * (other_perms_count // 2))
    if other_perms_count % 2 == 1:
        layout.append(1)
    layout.append(2)  # 底部导航 (返回 + 主页)

    keyboard.adjust(*layout)
    return keyboard.as_markup()
