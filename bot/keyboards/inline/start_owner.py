from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.common_buttons import (
    ACCOUNT_CENTER_BUTTON,
    ADMIN_PANEL_BUTTON,
    BACK_BUTTON,
    BACK_TO_HOME_BUTTON,
    OWNER_PANEL_BUTTON,
    PROFILE_BUTTON,
)
from bot.keyboards.inline.labels import (
    ADMIN_FEATURES_SWITCH_LABEL,
    ADMIN_LIST_LABEL,
    ADMIN_NEW_ITEM_NOTIFICATION_LABEL,
    ADMIN_PERMS_PANEL_LABEL,
    BACK_LABEL,
    BACK_TO_HOME_LABEL,
    FEATURES_PANEL_LABEL,
    GROUPS_LABEL,
    HITOKOTO_LABEL,
    OPEN_REGISTRATION_LABEL,
    OWNER_ADMINS_LABEL,
    ROBOT_SWITCH_LABEL,
    STATS_LABEL,
    USER_DEVICES_LABEL,
    USER_FEATURES_SWITCH_LABEL,
    USER_INFO_LABEL,
    USER_LINES_LABEL,
    USER_PASSWORD_LABEL,
    USER_REGISTER_LABEL,
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
    buttons = [
        [InlineKeyboardButton(text=OWNER_ADMINS_LABEL, callback_data="owner:admins")],
        [InlineKeyboardButton(text=FEATURES_PANEL_LABEL, callback_data="owner:features")],
        [InlineKeyboardButton(text=ADMIN_PERMS_PANEL_LABEL, callback_data="owner:admin_perms")],
        [BACK_TO_HOME_BUTTON],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()


def get_features_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """功能开关面板键盘

    功能说明:
    - 控制用户功能的开关, 使用状态 emoji (🟢/🔴) 清晰显示开启关闭
    - 底部包含返回上一级与返回主面板按钮

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 功能开关键盘
    """

    def status(v: bool) -> str:
        return "🟢" if v else "🔴"

    buttons = [
        [
            InlineKeyboardButton(
                text=f"{ROBOT_SWITCH_LABEL} {status(features.get('bot.features.enabled', False))}",
                callback_data="owner:features:toggle:bot_all",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{USER_FEATURES_SWITCH_LABEL} {status(features.get('user.features.enabled', False))}",
                callback_data="owner:features:toggle:user_all",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{USER_REGISTER_LABEL} {status(features.get('user.register', False))}",
                callback_data="owner:features:toggle:user_register",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{USER_INFO_LABEL} {status(features.get('user.info', False))}",
                callback_data="owner:features:toggle:user_info",
            ),
            InlineKeyboardButton(
                text=f"{USER_LINES_LABEL} {status(features.get('user.lines', False))}",
                callback_data="owner:features:toggle:user_lines",
            ),
        ],
        [
            InlineKeyboardButton(
                text=f"{USER_DEVICES_LABEL} {status(features.get('user.devices', False))}",
                callback_data="owner:features:toggle:user_devices",
            ),
            InlineKeyboardButton(
                text=f"{USER_PASSWORD_LABEL} {status(features.get('user.password', False))}",
                callback_data="owner:features:toggle:user_password",
            ),
        ],
        [BACK_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2, 1, 2, 2, 2)
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
        [InlineKeyboardButton(text=ADMIN_LIST_LABEL, callback_data="owner:admins:list")],
        [InlineKeyboardButton(text=BACK_LABEL, callback_data="owner:panel")],
        [InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back")],
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

    def status(v: bool) -> str:
        return "🟢" if v else "🔴"

    buttons = [
        [
            InlineKeyboardButton(
                text=format_with_status(ADMIN_FEATURES_SWITCH_LABEL, perms.get("admin.features.enabled", False)),
                callback_data="owner:admin_perms:toggle:features",
            )
        ],
        [
            InlineKeyboardButton(
                text=format_with_status(GROUPS_LABEL, perms.get("admin.groups", False)),
                callback_data="owner:admin_perms:toggle:groups",
            )
        ],
        [
            InlineKeyboardButton(
                text=format_with_status(STATS_LABEL, perms.get("admin.stats", False)),
                callback_data="owner:admin_perms:toggle:stats",
            )
        ],
        [
            InlineKeyboardButton(
                text=format_with_status(OPEN_REGISTRATION_LABEL, perms.get("admin.open_registration", False)),
                callback_data="owner:admin_perms:toggle:open_registration",
            )
        ],
        [
            InlineKeyboardButton(
                text=format_with_status(HITOKOTO_LABEL, perms.get("admin.hitokoto", False)),
                callback_data="owner:admin_perms:toggle:hitokoto",
            )
        ],
        [
            InlineKeyboardButton(
                text=format_with_status(ADMIN_NEW_ITEM_NOTIFICATION_LABEL, perms.get("admin.new_item_notification", False)),
                callback_data="owner:admin_perms:toggle:new_item_notification",
            )
        ],
        [InlineKeyboardButton(text=BACK_LABEL, callback_data="owner:panel")],
        [InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back")],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(1, 2)
    return keyboard.as_markup()
