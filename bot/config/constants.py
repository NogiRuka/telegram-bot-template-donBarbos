"""
配置键常量定义

功能说明:
- 定义所有配置项的键名常量
- 按功能模块分类组织
- 便于统一管理和维护
"""

# 机器人功能配置
KEY_BOT_FEATURES_ENABLED = "bot.features.enabled"

# 用户功能配置
KEY_USER_FEATURES_ENABLED = "user.features.enabled"
KEY_USER_PROFILE = "user.profile"
KEY_USER_ACCOUNT = "user.account"
KEY_USER_REGISTER = "user.register"
KEY_USER_INFO = "user.info"
KEY_USER_LINES = "user.lines"
KEY_USER_LINES_INFO = "user.lines.info"
KEY_USER_LINES_NOTICE = "user.lines.notice"
KEY_USER_DEVICES = "user.devices"
KEY_USER_TAGS = "user.tags"
KEY_USER_AVATAR = "user.avatar"
KEY_USER_PASSWORD = "user.password"
KEY_USER_STORE = "user.store"
KEY_USER_CHECKIN = "user.checkin"

# 管理员功能配置
KEY_ADMIN_FEATURES_ENABLED = "admin.features.enabled"
KEY_ADMIN_GROUPS = "admin.groups"
KEY_ADMIN_STATS = "admin.stats"
KEY_ADMIN_HITOKOTO = "admin.hitokoto"
KEY_ADMIN_OPEN_REGISTRATION = "admin.open_registration"
KEY_ADMIN_NEW_ITEM_NOTIFICATION = "admin.new_item_notification"
KEY_ADMIN_ANNOUNCEMENT = "admin.announcement"
# 公告内容
KEY_ADMIN_ANNOUNCEMENT_TEXT = "admin.announcement.text"
KEY_ADMIN_STORE = "admin.store"
KEY_ADMIN_CURRENCY = "admin.currency"
KEY_ADMIN_MAIN_IMAGE = "admin.main_image"
KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED = "admin.main_image.nsfw_enabled"
KEY_ADMIN_FILES = "admin.files"
KEY_ADMIN_QUIZ = "admin.quiz"

# 注册相关配置
KEY_REGISTRATION_FREE_OPEN = "registration.free_open"
KEY_ADMIN_OPEN_REGISTRATION_WINDOW = "admin.open_registration.window"
KEY_ADMIN_HITOKOTO_CATEGORIES = "admin.hitokoto.categories"

# 问答配置
KEY_QUIZ_COOLDOWN_MINUTES = "admin.quiz.cooldown_minutes"
KEY_QUIZ_TRIGGER_PROBABILITY = "admin.quiz.trigger_probability"
KEY_QUIZ_DAILY_LIMIT = "admin.quiz.daily_limit"
KEY_QUIZ_SESSION_TIMEOUT = "admin.quiz.session_timeout"
KEY_QUIZ_GLOBAL_ENABLE = "admin.quiz.global_enable"
KEY_QUIZ_SCHEDULE_TIME = "admin.quiz.schedule.time"
KEY_QUIZ_SCHEDULE_TARGET_TYPE = "admin.quiz.schedule.target_type"
KEY_QUIZ_SCHEDULE_TARGET_COUNT = "admin.quiz.schedule.target_count"
KEY_QUIZ_SCHEDULE_ENABLE = "admin.quiz.schedule.enable"

# 通知配置
KEY_NOTIFICATION_CHANNELS = "notification.channels"
