from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import (
    ADMIN_PANEL_VISIBLE_FEATURES,
    ADMIN_FEATURES_MAPPING,
    KEY_ADMIN_FEATURES_ENABLED,
)
from bot.keyboards.inline.buttons import (
    MAIN_ADMIN_BUTTONS,
    BACK_TO_ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
    NOTIFY_SEND_BUTTON,
    MAIN_IMAGE_BACK_BUTTON,
    MAIN_IMAGE_CANCEL_BUTTON,
    MAIN_IMAGE_UPLOAD_SFW_BUTTON,
    MAIN_IMAGE_UPLOAD_NSFW_BUTTON,
    MAIN_IMAGE_BACK_TO_UPLOAD_BUTTON,
)
from bot.keyboards.inline.constants import (
    NOTIFY_COMPLETE_CALLBACK_DATA,
    NOTIFY_COMPLETE_LABEL,
    NOTIFY_PREVIEW_CALLBACK_DATA,
    NOTIFY_PREVIEW_LABEL,
    MAIN_IMAGE_ADMIN_CALLBACK_DATA,
    MAIN_IMAGE_UPLOAD_LABEL,
    MAIN_IMAGE_LIST_LABEL,
    MAIN_IMAGE_SCHEDULE_LABEL,
    MAIN_IMAGE_TEST_LABEL,
    MAIN_IMAGE_TOGGLE_NSFW_LABEL,
    MAIN_IMAGE_SCHEDULE_LIST_LABEL,
    MAIN_IMAGE_SCHEDULE_DELETE_LABEL,
    MAIN_IMAGE_CONTINUE_UPLOAD_LABEL,
    MAIN_IMAGE_UPLOAD_CALLBACK_DATA
)


def get_start_admin_keyboard() -> InlineKeyboardMarkup:
    """管理员首页键盘

    功能说明:
    - 采用 menu 风格布局, 提供用户基础入口与管理员面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = MAIN_ADMIN_BUTTONS
    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()


def get_admin_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员面板键盘

    功能说明:
    - 二级入口: 管理功能集合, 底部包含返回主面板

    输入参数:
    - features: 管理员功能开关映射

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons: list[list[InlineKeyboardButton]] = []
    master_enabled = features.get(KEY_ADMIN_FEATURES_ENABLED, False)

    for short_code in ADMIN_PANEL_VISIBLE_FEATURES:
        if short_code not in ADMIN_FEATURES_MAPPING:
            continue

        config_key, label = ADMIN_FEATURES_MAPPING[short_code]
        if master_enabled and features.get(config_key, False):
            buttons.append([InlineKeyboardButton(text=label, callback_data=f"admin:{short_code}")])

    buttons.append([BACK_TO_HOME_BUTTON])
    keyboard = InlineKeyboardBuilder(markup=buttons)

    # 动态调整布局: 每行2个, 最后1个返回键单独一行
    # 如果按钮数量(不含返回键)是奇数, 则最后一个功能键单独一行
    count = len(buttons) - 1
    layout = [2] * (count // 2)
    if count % 2 == 1:
        layout.append(1)
    layout.append(1)  # 返回键

    keyboard.adjust(*layout)
    return keyboard.as_markup()


def get_main_image_list_type_keyboard() -> InlineKeyboardMarkup:
    """获取主图列表分类选择键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="🟢 SFW", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list:view:sfw:1:5"),
            InlineKeyboardButton(text="🔞 NSFW", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list:view:nsfw:1:5"),
        ],
        [MAIN_IMAGE_BACK_BUTTON]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_image_list_pagination_keyboard(type_key: str, page: int, total_pages: int, limit: int) -> InlineKeyboardMarkup:
    """获取主图列表分页键盘
    
    输入参数:
    - type_key: sfw / nsfw
    - page: 当前页码
    - total_pages: 总页数
    - limit: 每页条数
    """
    # 翻页逻辑: 确保页码不越界
    prev_page = max(1, page - 1)
    next_page = min(total_pages, page + 1)
    
    # 切换每页条数: 5 -> 10 -> 20 -> 5
    next_limit = 10 if limit == 5 else (20 if limit == 10 else 5)
    
    buttons = [
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:list:view:{type_key}:{prev_page}:{limit}"),
            InlineKeyboardButton(text=f"{page}/{total_pages} (每页{limit}条)", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:list:view:{type_key}:1:{next_limit}"),
            InlineKeyboardButton(text="➡️", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:list:view:{type_key}:{next_page}:{limit}"),
        ],
        [
            InlineKeyboardButton(text="🔙 返回分类选择", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list"),
            InlineKeyboardButton(text="↩️ 返回主图管理", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list:back_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_image_admin_keyboard() -> InlineKeyboardMarkup:
    """主图管理面板键盘"""
    buttons = [
        [
            InlineKeyboardButton(text=MAIN_IMAGE_UPLOAD_LABEL, callback_data=MAIN_IMAGE_UPLOAD_CALLBACK_DATA),
            InlineKeyboardButton(text=MAIN_IMAGE_LIST_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list"),
        ],
        [
            InlineKeyboardButton(text=MAIN_IMAGE_SCHEDULE_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule"),
            InlineKeyboardButton(text=MAIN_IMAGE_TEST_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":test"),
        ],
        [
            InlineKeyboardButton(text=MAIN_IMAGE_TOGGLE_NSFW_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":toggle_nsfw"),
        ],
        [BACK_TO_ADMIN_PANEL_BUTTON]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_image_item_keyboard(image_id: int, is_enabled: bool) -> InlineKeyboardMarkup:
    """获取单张主图的操作键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="🔴 禁用" if is_enabled else "🟢 启用", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:item:toggle:{image_id}"),
            InlineKeyboardButton(text="🗑️ 删除", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:item:delete:{image_id}"),
            InlineKeyboardButton(text="❌ 关闭", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:item:close"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_notification_panel_keyboard(pending_completion: int, pending_review: int) -> InlineKeyboardMarkup:
    """获取上新通知管理面板键盘

    功能说明:
    - 包含 [上新补全]、[上新预览]、[一键通知] 三个主要功能按钮
    - 底部包含 [返回上一级] (到管理员面板) 和 [返回主页]

    输入参数:
    - pending_completion: 待补全数量
    - pending_review: 待审核数量

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{NOTIFY_COMPLETE_LABEL} ({pending_completion})",
                callback_data=NOTIFY_COMPLETE_CALLBACK_DATA,
            ),
            InlineKeyboardButton(
                text=f"{NOTIFY_PREVIEW_LABEL} ({pending_review})",
                callback_data=NOTIFY_PREVIEW_CALLBACK_DATA,
            ),
        ],
        [NOTIFY_SEND_BUTTON],
        [BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_main_image_back_keyboard() -> InlineKeyboardMarkup:
    """主图管理返回键盘 (用于列表/查看等非输入状态)"""
    buttons = [[MAIN_IMAGE_BACK_BUTTON, BACK_TO_HOME_BUTTON]]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_main_image_cancel_keyboard() -> InlineKeyboardMarkup:
    """主图管理取消键盘 (用于输入状态)"""
    buttons = [[MAIN_IMAGE_CANCEL_BUTTON]]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_main_image_upload_type_keyboard() -> InlineKeyboardMarkup:
    """主图上传类型选择键盘"""
    buttons = [
        [MAIN_IMAGE_UPLOAD_SFW_BUTTON, MAIN_IMAGE_UPLOAD_NSFW_BUTTON],
        [MAIN_IMAGE_BACK_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()
