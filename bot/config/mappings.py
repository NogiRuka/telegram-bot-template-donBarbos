"""
功能映射配置定义

功能说明:
- 定义各种功能开关的映射关系
- 用于管理员面板和用户功能管理
- 格式: 短代码 -> (配置键, 显示标签)
"""

from typing import Any

from .constants import *
from bot.database.models.config import ConfigType
from bot.keyboards.inline.constants import *

# 默认配置值定义
# 格式: Key -> (Value, ConfigType)
DEFAULT_CONFIGS: dict[str, tuple[Any, ConfigType]] = {
    # 基础开关配置 (布尔值)
    KEY_BOT_FEATURES_ENABLED: (True, ConfigType.BOOLEAN),
    KEY_USER_FEATURES_ENABLED: (True, ConfigType.BOOLEAN),
    KEY_USER_PROFILE: (True, ConfigType.BOOLEAN),
    KEY_USER_ACCOUNT: (True, ConfigType.BOOLEAN),
    KEY_USER_REGISTER: (True, ConfigType.BOOLEAN),
    KEY_USER_INFO: (True, ConfigType.BOOLEAN),
    KEY_USER_LINES: (True, ConfigType.BOOLEAN),
    KEY_USER_DEVICES: (True, ConfigType.BOOLEAN),
    KEY_USER_TAGS: (True, ConfigType.BOOLEAN),
    KEY_USER_AVATAR: (True, ConfigType.BOOLEAN),
    KEY_USER_PASSWORD: (True, ConfigType.BOOLEAN),
    KEY_USER_STORE: (True, ConfigType.BOOLEAN),
    KEY_USER_CHECKIN: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_FEATURES_ENABLED: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_GROUPS: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_STATS: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_OPEN_REGISTRATION: (True, ConfigType.BOOLEAN),
    KEY_REGISTRATION_FREE_OPEN: (False, ConfigType.BOOLEAN),
    KEY_ADMIN_HITOKOTO: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_NEW_ITEM_NOTIFICATION: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_ANNOUNCEMENT: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_STORE: (True, ConfigType.BOOLEAN),
    KEY_ADMIN_CURRENCY: (True, ConfigType.BOOLEAN),
    
    # 复杂类型配置
    KEY_ADMIN_HITOKOTO_CATEGORIES: (["d", "i"], ConfigType.LIST),
    # KEY_USER_LINES_INFO 的初始化逻辑比较特殊（依赖环境变量），保留在 config_service 中处理，或可在此定义空值
    KEY_USER_LINES_INFO: (None, ConfigType.JSON),
    KEY_USER_LINES_NOTICE: (
        "关于Emby：[Emby百科](https://emby.wiki)\n"
        "任何问题请通过[频道](https://t.me/lustfulboy_channel?direct)私信\n"
        "注意事项：\n"
        "🚫 泄露服务器地址\n"
        "🚫 网页端播放\n"
        "🚫 网易爆米花\n"
        "🚫 创建播放列表\n"
        "🚫 Infuse媒体库模式",
        ConfigType.STRING
    ),
    KEY_ADMIN_ANNOUNCEMENT_TEXT: ("", ConfigType.STRING),
}

# 用户功能开关映射 - 用于用户功能管理
USER_FEATURES_MAPPING: dict[str, tuple[str, str]] = {
    "bot": (KEY_BOT_FEATURES_ENABLED, ROBOT_SWITCH_LABEL),
    "all": (KEY_USER_FEATURES_ENABLED, USER_FEATURES_SWITCH_LABEL),
    "profile": (KEY_USER_PROFILE, PROFILE_LABEL),
    "account": (KEY_USER_ACCOUNT, ACCOUNT_CENTER_LABEL),
    "register": (KEY_USER_REGISTER, USER_REGISTER_LABEL),
    "info": (KEY_USER_INFO, USER_INFO_LABEL),
    "lines": (KEY_USER_LINES, USER_LINES_LABEL),
    "devices": (KEY_USER_DEVICES, USER_DEVICES_LABEL),
    "tags": (KEY_USER_TAGS, USER_TAGS_LABEL),
    "avatar": (KEY_USER_AVATAR, USER_AVATAR_LABEL),
    "password": (KEY_USER_PASSWORD, USER_PASSWORD_LABEL),
    "store": (KEY_USER_STORE, ESSENCE_STORE_LABEL),
    "checkin": (KEY_USER_CHECKIN, DAILY_CHECKIN_LABEL),
}

# 管理员功能映射 - 用于管理员权限控制
ADMIN_FEATURES_MAPPING: dict[str, tuple[str, str]] = {
    "features": (KEY_ADMIN_FEATURES_ENABLED, ADMIN_FEATURES_SWITCH_LABEL),
    "groups": (KEY_ADMIN_GROUPS, GROUPS_LABEL),
    "stats": (KEY_ADMIN_STATS, STATS_LABEL),
    "hitokoto": (KEY_ADMIN_HITOKOTO, HITOKOTO_LABEL),
    "open_registration": (KEY_ADMIN_OPEN_REGISTRATION, OPEN_REGISTRATION_LABEL),
    "new_item_notification": (KEY_ADMIN_NEW_ITEM_NOTIFICATION, ADMIN_NEW_ITEM_NOTIFICATION_LABEL),
    "copywriting": (KEY_ADMIN_ANNOUNCEMENT, COPYWRITING_LABEL),
    "store": (KEY_ADMIN_STORE, STORE_ADMIN_LABEL),
    "currency": (KEY_ADMIN_CURRENCY, CURRENCY_ADMIN_LABEL),
}

# 在管理员面板中拥有独立按钮的功能
ADMIN_PANEL_VISIBLE_FEATURES: list[str] = [
    "groups",
    "stats",
    "hitokoto",
    "open_registration",
    "new_item_notification",
    "copywriting",
    "store",
    "currency",
]
