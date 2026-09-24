"""键盘通用文案与格式化工具

功能说明:
- 统一维护跨面板重复使用的按钮文案, 避免多处定义造成不一致
- 提供带开关状态的文案格式化工具, 使用 🟢/🔴 呈现启用/禁用

依赖说明:
- 无外部库依赖

命名风格:
- 常量使用大写加下划线
"""
from bot.core.constants import CURRENCY_SYMBOL

# ===== 用户功能 =====
# 个人中心
PROFILE_LABEL = "👤 个人中心"
BACK_TO_PROFILE_LABEL = "↩️ 返回个人中心"
PROFILE_CALLBACK_DATA = "user:profile"
PROFILE_MAIN_IMAGE_LABEL = "🖼️ 主图设置"
PROFILE_MAIN_IMAGE_CALLBACK_DATA = "user:profile:main_image"

# 求片/投稿
USER_SUBMISSION_LABEL = "📝 求片/投稿"
USER_SUBMISSION_CALLBACK_DATA = "user:submission"
BACK_TO_USER_SUBMISSION_LABEL = "↩️ 返回求片/投稿"

# 问答投稿（保留兼容）
USER_QUIZ_SUBMIT_LABEL = "✍️ 问答投稿"
USER_QUIZ_SUBMIT_CALLBACK_DATA = "user:quiz:submit"

# 账号中心
ACCOUNT_CENTER_LABEL = "🎬 账号中心"
ACCOUNT_CENTER_CALLBACK_DATA = "user:account"

# 注册相关
START_REGISTER_LABEL = "🔥 开始注册"
START_REGISTER_CALLBACK_DATA = "user:register"
CANCEL_REGISTER_LABEL = "❌ 取消注册"
CANCEL_REGISTER_CALLBACK_DATA = "user:cancel_register"

# 账号信息
USER_INFO_LABEL = "👤 账号信息"
USER_INFO_CALLBACK_DATA = "user:info"

# 线路信息
USER_LINES_LABEL = "🛰️ 线路信息"
USER_LINES_CALLBACK_DATA = "user:lines"

# 设备管理
USER_DEVICES_LABEL = "📱 设备管理"
USER_DEVICES_CALLBACK_DATA = "user:devices"

# 标签屏蔽
USER_TAGS_LABEL = "🚫 标签屏蔽"
USER_TAGS_CALLBACK_DATA = "user:tags"
TAGS_CUSTOM_LABEL = "✏️ 自定义屏蔽"
TAGS_CUSTOM_CALLBACK_DATA = "user:tags:custom"
TAGS_CLEAR_LABEL = "🗑️ 清除所有屏蔽"
TAGS_CLEAR_CALLBACK_DATA = "user:tags:clear"
TAGS_CANCEL_EDIT_LABEL = "❌ 取消编辑"
TAGS_CANCEL_EDIT_CALLBACK_DATA = "user:tags:cancel_edit"

# 修改头像
USER_AVATAR_LABEL = "🖼️ 修改头像"
USER_AVATAR_CALLBACK_DATA = "user:avatar"

# 修改密码
USER_PASSWORD_LABEL = "🔐 修改密码"
USER_PASSWORD_CALLBACK_DATA = "user:password"
CANCEL_PASSWORD_CHANGE_LABEL = "❌ 取消修改"
CANCEL_PASSWORD_CHANGE_CALLBACK_DATA = "user:cancel_password"

# 返回账号中心
BACK_TO_ACCOUNT_LABEL = "↩️ 返回账号中心"
BACK_TO_ACCOUNT_CALLBACK_DATA = "user:account"

# 签到与商店
DAILY_CHECKIN_LABEL = f"{CURRENCY_SYMBOL} 每日签到"
DAILY_CHECKIN_CALLBACK_DATA = "user:checkin"

ESSENCE_STORE_LABEL = "💎 精粹商店"
ESSENCE_STORE_CALLBACK_DATA = "user:store"
STORE_PRODUCT_PREFIX = "store:product:"
STORE_BUY_PREFIX = "store:buy:"
BACK_TO_STORE_LABEL = "🔙 返回商店"





# ===== 管理员功能 =====
# 管理员面板
ADMIN_PANEL_LABEL = "🛡️ 管理员面板"
ADMIN_PANEL_CALLBACK_DATA = "admin:panel"

# 群组管理
GROUPS_LABEL = "👥 群组管理"
GROUPS_CALLBACK_DATA = "admin:groups"

# 统计数据
STATS_LABEL = "📊 统计数据"
STATS_CALLBACK_DATA = "admin:stats"

# 开放注册
OPEN_REGISTRATION_LABEL = "🛂 开放注册"
OPEN_REGISTRATION_CALLBACK_DATA = "admin:registration"

# 一言管理
HITOKOTO_LABEL = "🎴 一言管理"
HITOKOTO_CALLBACK_DATA = "admin:hitokoto"

# 新片通知
ADMIN_NEW_ITEM_NOTIFICATION_LABEL = "🎬 新片通知"
ADMIN_NEW_ITEM_NOTIFICATION_CALLBACK_DATA = "admin:notify"

# 文案管理
COPYWRITING_LABEL = "📝 文案管理"
ADMIN_COPYWRITING_CALLBACK_DATA = "admin:copywriting"
BACK_TO_COPYWRITING_LABEL = "🔙 返回文案列表"


# 商店管理
STORE_ADMIN_LABEL = "🏪 商店管理"
STORE_ADMIN_CALLBACK_DATA = "admin:store"
STORE_ADMIN_PRODUCT_PREFIX = "admin:store:product:"
STORE_ADMIN_EDIT_PREFIX = "admin:store:edit:"
STORE_ADMIN_TOGGLE_PREFIX = "admin:store:toggle:"
STORE_ADMIN_ADD_PRODUCT_LABEL = "➕ 添加商品"
STORE_ADMIN_ADD_PRODUCT_CALLBACK_DATA = "admin:store:add"

# 购买记录
STORE_ADMIN_HISTORY_LABEL = "📜 购买记录"
STORE_ADMIN_HISTORY_CALLBACK_DATA = "admin:store:history"

# 精粹管理
CURRENCY_ADMIN_LABEL = "💎 精粹管理"
CURRENCY_ADMIN_CALLBACK_DATA = "admin:currency"

# 主图管理
MAIN_IMAGE_ADMIN_LABEL = "🖼 主图管理"
MAIN_IMAGE_ADMIN_CALLBACK_DATA = "admin:main_image"
MAIN_IMAGE_UPLOAD_LABEL = "📤 上传图片"
MAIN_IMAGE_UPLOAD_CALLBACK_DATA = "admin:main_image:upload"
MAIN_IMAGE_LIST_LABEL = "🗂 图片列表"
MAIN_IMAGE_LIST_CALLBACK_DATA = "admin:main_image:list"
MAIN_IMAGE_SCHEDULE_LABEL = "📆 节日投放"
MAIN_IMAGE_SCHEDULE_CALLBACK_DATA = "admin:main_image:schedule"
MAIN_IMAGE_SCHEDULE_DELETE_LABEL = "🗑️ 删除投放"
MAIN_IMAGE_SCHEDULE_DELETE_CALLBACK_DATA = "admin:main_image:schedule_delete"
MAIN_IMAGE_SCHEDULE_LIST_LABEL = "📜 查看投放"
MAIN_IMAGE_SCHEDULE_LIST_CALLBACK_DATA = "admin:main_image:schedule_list"
MAIN_IMAGE_TEST_LABEL = "🧪 图片测试"
MAIN_IMAGE_TEST_CALLBACK_DATA = "admin:main_image:test"
MAIN_IMAGE_TOGGLE_NSFW_LABEL = "🔞 NSFW 开关"
MAIN_IMAGE_TOGGLE_NSFW_CALLBACK_DATA = "admin:main_image:toggle_nsfw"
MAIN_IMAGE_BACK_LABEL = "↩️ 返回主图管理"
MAIN_IMAGE_CANCEL_LABEL = "❌ 取消"
MAIN_IMAGE_UPLOAD_SFW_LABEL = "🟢 上传 SFW"

# ===== 问答管理 =====
QUIZ_ADMIN_LABEL = "🎲 问答管理"
QUIZ_ADMIN_CALLBACK_DATA = "admin:quiz"
QUIZ_ADMIN_BACK_LABEL = "↩️ 返回问答管理"

QUIZ_ADMIN_ADD_QUICK_LABEL = "➕ 添加题目"

QUIZ_ADMIN_TRIGGER_LABEL = "⚙️ 触发设置"

QUIZ_ADMIN_LIST_QUESTIONS_LABEL = "📋 题目列表"

QUIZ_ADMIN_LIST_IMAGES_LABEL = "🖼️ 题图列表"

QUIZ_ADMIN_CATEGORY_LABEL = "🏷️ 分类管理"

QUIZ_ADMIN_TEST_TRIGGER_LABEL = "🧪 题目测试"

# 问答列表相关
QUIZ_ADMIN_LIST_MENU_LABEL = "📋 查看列表"
QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA = "admin:quiz:list_menu"
QUIZ_ADMIN_LIST_QUIZZES_LABEL = "💭 题库预览"

# 问答设置
QUIZ_ADMIN_SETTINGS_MENU_LABEL = "⚙️ 修改设置"
QUIZ_ADMIN_SCHEDULE_MENU_LABEL = "⏰ 定时触发设置"

QUIZ_ADMIN_SET_PROBABILITY_LABEL = "🎲 修改触发概率"
QUIZ_ADMIN_SET_COOLDOWN_LABEL = "⏳ 修改冷却时间"
QUIZ_ADMIN_SET_DAILY_LIMIT_LABEL = "🔢 修改每日上限"
QUIZ_ADMIN_SET_TIMEOUT_LABEL = "⏱️ 修改答题限时"

# 定时设置相关
QUIZ_ADMIN_SCHEDULE_SET_TIME_LABEL = "🕒 设置时间"
QUIZ_ADMIN_SCHEDULE_SET_TARGET_LABEL = "👥 设置对象"
QUIZ_ADMIN_SCHEDULE_TOGGLE_LABEL = "🔘 定时开关"
MAIN_IMAGE_UPLOAD_NSFW_LABEL = "🔞 上传 NSFW"
MAIN_IMAGE_CONTINUE_UPLOAD_LABEL = "📤 继续上传"
MAIN_IMAGE_BACK_TO_UPLOAD_LABEL = "↩️ 返回上传选择"

# 上新补全
NOTIFY_COMPLETE_LABEL = "🔄 上新补全"
NOTIFY_COMPLETE_CALLBACK_DATA = "admin:notify_complete"

# 上新预览
NOTIFY_PREVIEW_LABEL = "👀 上新预览"
NOTIFY_PREVIEW_CALLBACK_DATA = "admin:notify_preview"

# 预览转补全
NOTIFY_PREVIEW_TO_COMPLETE_LABEL = "🔄 预览转补全"
NOTIFY_PREVIEW_TO_COMPLETE_CALLBACK_DATA = "admin:notify_preview_to_complete"

# 关闭预览
NOTIFY_CLOSE_PREVIEW_LABEL = "❌ 关闭预览"
CLOSE_LABEL = "❌ 关闭"
NOTIFY_CLOSE_PREVIEW_CALLBACK_DATA = "delete_msg"

# 一键通知
NOTIFY_SEND_LABEL = "🚀 一键通知"
NOTIFY_SEND_CALLBACK_DATA = "admin:notify_send"

NOTIFY_SETTINGS_LABEL = "⚙️ 通知设置"
NOTIFY_SETTINGS_CALLBACK_DATA = "admin:notify_settings"
NOTIFY_SETTINGS_TOGGLE_CALLBACK_DATA = "admin:notify_settings:toggle"

# 确认发送
NOTIFY_CONFIRM_SEND_LABEL = "🚀 确认发送"
NOTIFY_CONFIRM_SEND_CALLBACK_DATA = "admin:notify_confirm_send"

# 通用取消
NOTIFY_CONFIRM_SEND_CANCEL_LABEL = "❌ 取消"
NOTIFY_CONFIRM_SEND_CANCEL_CALLBACK_DATA = "admin:new_item_notification"

# 返回管理员面板
BACK_TO_ADMIN_PANEL_LABEL = "↩️ 返回管理员面板"
BACK_TO_ADMIN_PANEL_CALLBACK_DATA = "admin:panel"


# ===== 所有者功能 =====
# 所有者面板
OWNER_PANEL_LABEL = "👑 所有者面板"
OWNER_PANEL_CALLBACK_DATA = "owner:panel"

# 功能开关
USER_FEATURES_PANEL_LABEL = "🧩 用户功能开关"
USER_FEATURES_PANEL_CALLBACK_DATA = "owner:user_features"

# 用户注册
USER_REGISTER_LABEL = "🔥 用户注册"
USER_REGISTER_CALLBACK_DATA = "owner:user_register"

# 机器人开关
ROBOT_SWITCH_LABEL = "🤖 机器人开关"
ROBOT_SWITCH_CALLBACK_DATA = "owner:robot_switch"

# 用户总开关
USER_FEATURES_SWITCH_LABEL = "🧲 用户总开关"
USER_FEATURES_SWITCH_CALLBACK_DATA = "owner:user_features"

# 管理员权限
ADMIN_FEATURES_PANEL_LABEL = "🛡️ 管理员功能"
ADMIN_FEATURES_PANEL_CALLBACK_DATA = "owner:admin_features"

# 管理员总开关
ADMIN_FEATURES_SWITCH_LABEL = "🧲 管理员总开关"
ADMIN_FEATURES_SWITCH_CALLBACK_DATA = "owner:admin_features"
ADMIN_FEATURES_TOGGLE_FEATURES_CALLBACK_DATA = "owner:admin_features:toggle:features"

# 返回所有者面板
BACK_TO_OWNER_PANEL_LABEL = "↩️ 返回所有者面板"
BACK_TO_OWNER_PANEL_CALLBACK_DATA = "owner:panel"


# ===== 通用导航 =====
BACK_TO_HOME_LABEL = "🏠 返回主面板"
BACK_TO_HOME_CALLBACK_DATA = "back:home"

# ===== 群组配置 =====
# 返回主面板（群组配置使用）
GROUP_BACK_TO_HOME_LABEL = "↩️ 返回主面板"
GROUP_BACK_TO_HOME_CALLBACK_DATA = "home:back"

# ===== 文件管理 =====
FILE_ADMIN_LABEL = "📁 文件管理"
FILE_ADMIN_CALLBACK_DATA = "admin:files"
FILE_SAVE_LABEL = "💾 保存文件"
FILE_SAVE_CALLBACK_DATA = "admin:files:save"
FILE_LIST_LABEL = "📜 查看文件"
FILE_LIST_CALLBACK_DATA = "admin:files:list"

# ===== 问答管理 =====
QUIZ_ADMIN_LABEL = "🎲 问答管理"
QUIZ_ADMIN_CALLBACK_DATA = "admin:quiz"


def format_with_status(label: str, enabled: bool) -> str:
    """格式化带状态的文案

    功能说明:
    - 返回 "<label> <状态>" 格式的文本, 状态使用 🟢/🔴 显示启用/禁用

    输入参数:
    - label: 基础文案
    - enabled: 是否启用

    返回值:
    - str: 格式化后的文案
    """
    return f"{label} {'🟢' if enabled else '🔴'}"
