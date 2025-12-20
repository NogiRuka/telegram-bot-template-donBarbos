"""
功能映射配置定义

功能说明:
- 定义各种功能开关的映射关系
- 用于管理员面板和用户功能管理
- 格式: 短代码 -> (配置键, 显示标签)
"""

from .constants import *
from bot.keyboards.inline.constants import (
    ACCOUNT_CENTER_LABEL,
    ADMIN_FEATURES_SWITCH_LABEL,
    ADMIN_NEW_ITEM_NOTIFICATION_LABEL,
    GROUPS_LABEL,
    HITOKOTO_LABEL,
    OPEN_REGISTRATION_LABEL,
    PROFILE_LABEL,
    ROBOT_SWITCH_LABEL,
    STATS_LABEL,
    USER_DEVICES_LABEL,
    USER_FEATURES_SWITCH_LABEL,
    USER_INFO_LABEL,
    USER_LINES_LABEL,
    USER_PASSWORD_LABEL,
    USER_REGISTER_LABEL,
    USER_TAGS_LABEL,
)

# 默认配置值
DEFAULT_CONFIGS: dict[str, bool] = {
    KEY_BOT_FEATURES_ENABLED: True,
    KEY_USER_FEATURES_ENABLED: True,
    KEY_USER_REGISTER: True,
    KEY_USER_PASSWORD: True,
    KEY_USER_INFO: True,
    KEY_USER_LINES: True,
    KEY_USER_DEVICES: True,
    KEY_USER_PROFILE: True,
    KEY_USER_ACCOUNT: True,
    KEY_USER_TAGS: True,
    KEY_ADMIN_FEATURES_ENABLED: True,
    KEY_ADMIN_GROUPS: True,
    KEY_ADMIN_STATS: True,
    KEY_ADMIN_OPEN_REGISTRATION: True,
    KEY_REGISTRATION_FREE_OPEN: False,
    KEY_ADMIN_HITOKOTO: True,
    KEY_ADMIN_NEW_ITEM_NOTIFICATION: True,
}

# 所有者功能映射 - 用于管理员面板
OWNER_FEATURES_MAPPING: dict[str, tuple[str, str]] = {
    "bot_all": (KEY_BOT_FEATURES_ENABLED, ROBOT_SWITCH_LABEL),
    "user_all": (KEY_USER_FEATURES_ENABLED, USER_FEATURES_SWITCH_LABEL),
    "user_register": (KEY_USER_REGISTER, USER_REGISTER_LABEL),
    "user_info": (KEY_USER_INFO, USER_INFO_LABEL),
    "user_password": (KEY_USER_PASSWORD, USER_PASSWORD_LABEL),
    "user_lines": (KEY_USER_LINES, USER_LINES_LABEL),
    "user_devices": (KEY_USER_DEVICES, USER_DEVICES_LABEL),
    "user_profile": (KEY_USER_PROFILE, PROFILE_LABEL),
    "user_account": (KEY_USER_ACCOUNT, ACCOUNT_CENTER_LABEL),
    "user_tags": (KEY_USER_TAGS, USER_TAGS_LABEL),
    "admin_open_registration": (KEY_ADMIN_OPEN_REGISTRATION, OPEN_REGISTRATION_LABEL),
}

# 用户功能开关映射 - 用于用户功能管理
USER_FEATURES_MAPPING: dict[str, tuple[str, str]] = {
    "bot_all": (KEY_BOT_FEATURES_ENABLED, ROBOT_SWITCH_LABEL),
    "user_all": (KEY_USER_FEATURES_ENABLED, USER_FEATURES_SWITCH_LABEL),
    "user_profile": (KEY_USER_PROFILE, PROFILE_LABEL),
    "user_account": (KEY_USER_ACCOUNT, ACCOUNT_CENTER_LABEL),
    "user_register": (KEY_USER_REGISTER, USER_REGISTER_LABEL),
    "user_info": (KEY_USER_INFO, USER_INFO_LABEL),
    "user_lines": (KEY_USER_LINES, USER_LINES_LABEL),
    "user_devices": (KEY_USER_DEVICES, USER_DEVICES_LABEL),
    "user_password": (KEY_USER_PASSWORD, USER_PASSWORD_LABEL),
    "user_tags": (KEY_USER_TAGS, USER_TAGS_LABEL),
}

# 管理员权限映射 - 用于管理员权限管理
ADMIN_PERMISSIONS_MAPPING: dict[str, tuple[str, str]] = {
    "features": (KEY_ADMIN_FEATURES_ENABLED, ADMIN_FEATURES_SWITCH_LABEL),
    "groups": (KEY_ADMIN_GROUPS, GROUPS_LABEL),
    "stats": (KEY_ADMIN_STATS, STATS_LABEL),
    "hitokoto": (KEY_ADMIN_HITOKOTO, HITOKOTO_LABEL),
    "open_registration": (KEY_ADMIN_OPEN_REGISTRATION, OPEN_REGISTRATION_LABEL),
    "new_item_notification": (KEY_ADMIN_NEW_ITEM_NOTIFICATION, ADMIN_NEW_ITEM_NOTIFICATION_LABEL),
}

# 在管理员面板中拥有独立按钮的功能
ADMIN_PANEL_VISIBLE_FEATURES: list[str] = [
    "groups",
    "stats",
    "hitokoto",
    "open_registration",
    "new_item_notification",
]
