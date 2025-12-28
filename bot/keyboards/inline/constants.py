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
# 个人信息
PROFILE_LABEL = "👤 个人信息"
PROFILE_CALLBACK_DATA = "user:profile"

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

# 修改密码
USER_PASSWORD_LABEL = "🔐 修改密码"
USER_PASSWORD_CALLBACK_DATA = "user:password"

# 修改头像
USER_AVATAR_LABEL = "🖼️ 修改头像"
USER_AVATAR_CALLBACK_DATA = "user:avatar"

# 标签屏蔽
USER_TAGS_LABEL = "🚫 标签屏蔽"
USER_TAGS_CALLBACK_DATA = "user:tags"
TAGS_CUSTOM_LABEL = "✏️ 自定义屏蔽"
TAGS_CUSTOM_CALLBACK_DATA = "user:tags:custom"
TAGS_CLEAR_LABEL = "🗑️ 清除所有屏蔽"
TAGS_CLEAR_CALLBACK_DATA = "user:tags:clear"
TAGS_CANCEL_EDIT_LABEL = "❌ 取消编辑"
TAGS_CANCEL_EDIT_CALLBACK_DATA = "user:tags:cancel_edit"

# 返回账号中心
BACK_TO_ACCOUNT_LABEL = "↩️ 返回账号中心"
BACK_TO_ACCOUNT_CALLBACK_DATA = "user:account"

# 取消修改密码
CANCEL_PASSWORD_CHANGE_LABEL = "❌ 取消修改"
CANCEL_PASSWORD_CHANGE_CALLBACK_DATA = "user:cancel_password"

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

# 上新补全
NOTIFY_COMPLETE_LABEL = "🔄 上新补全"
NOTIFY_COMPLETE_CALLBACK_DATA = "admin:notify_complete"

# 上新预览
NOTIFY_PREVIEW_LABEL = "👀 上新预览"
NOTIFY_PREVIEW_CALLBACK_DATA = "admin:notify_preview"

# 关闭预览
NOTIFY_CLOSE_PREVIEW_LABEL = "❌ 关闭预览"
NOTIFY_CLOSE_PREVIEW_CALLBACK_DATA = "admin:notify_close_preview"

# 一键通知
NOTIFY_SEND_LABEL = "🚀 一键通知"
NOTIFY_SEND_CALLBACK_DATA = "admin:notify_send"

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

# 管理员管理
OWNER_ADMINS_LABEL = "👮 管理员管理"
OWNER_ADMINS_CALLBACK_DATA = "owner:admins"

# 查看管理员列表
ADMIN_LIST_LABEL = "👀 查看管理员列表"
ADMIN_LIST_CALLBACK_DATA = "owner:admin_list"
ADMIN_LIST_VIEW_CALLBACK_DATA = "owner:admins:list"

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
