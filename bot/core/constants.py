"""
通用常量定义

功能说明:
- 存放项目中使用的各种常量
- 便于统一管理和维护
"""

# 经济系统常量
CURRENCY_NAME = "精粹"
CURRENCY_SYMBOL = "💧"

# Emby Webhook 事件类型常量
EVENT_TYPE_LIBRARY_NEW = "library.new"
EVENT_TYPE_PLAYBACK_START = "playback.start"
EVENT_TYPE_PLAYBACK_STOP = "playback.stop"
EVENT_TYPE_PLAYBACK_PAUSE = "playback.pause"
EVENT_TYPE_PLAYBACK_UNPAUSE = "playback.unpause"
EVENT_TYPE_USER_AUTHENTICATION = "user.authentication"
EVENT_TYPE_USER_LOCKED = "user.locked"
EVENT_TYPE_USER_UNLOCKED = "user.unlocked"
EVENT_TYPE_SERVER_SHUTDOWN = "server.shutdown"
EVENT_TYPE_SERVER_RESTART = "server.restart"

# 通知状态常量
NOTIFICATION_STATUS_PENDING_COMPLETION = "pending_completion"
NOTIFICATION_STATUS_PENDING_REVIEW = "pending_review"
NOTIFICATION_STATUS_SENT = "sent"
NOTIFICATION_STATUS_FAILED = "failed"
NOTIFICATION_STATUS_REJECTED = "rejected"

# 主图展示模式
DISPLAY_MODE_SFW = "sfw"
DISPLAY_MODE_NSFW = "nsfw"
DISPLAY_MODE_RANDOM = "random"

# 商店商品 Action Type
PRODUCT_ACTION_RETRO_CHECKIN = "retro_checkin"
PRODUCT_ACTION_EMBY_IMAGE = "emby_image"
PRODUCT_ACTION_EMBY_PASSWORD = "emby_password"
PRODUCT_ACTION_CUSTOM_TITLE = "custom_title"
PRODUCT_ACTION_MAIN_IMAGE_UNLOCK_NSFW = "main_image_unlock_nsfw"

# 配置键常量
CONFIG_KEY_EMBY_WHITELIST_USER_IDS = "emby_whitelist_user_ids"
