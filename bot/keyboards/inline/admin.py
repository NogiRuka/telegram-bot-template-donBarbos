from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import (
    ADMIN_FEATURES_MAPPING,
    ADMIN_PANEL_VISIBLE_FEATURES,
    KEY_ADMIN_FEATURES_ENABLED,
)
from bot.keyboards.inline.buttons import (
    BACK_TO_ADMIN_PANEL_BUTTON,
    BACK_TO_HOME_BUTTON,
    BACK_TO_QUIZ_ADMIN_BUTTON,
    MAIN_ADMIN_BUTTONS,
    MAIN_IMAGE_BACK_BUTTON,
    MAIN_IMAGE_BACK_TO_UPLOAD_BUTTON,
    MAIN_IMAGE_CANCEL_BUTTON,
    MAIN_IMAGE_UPLOAD_NSFW_BUTTON,
    MAIN_IMAGE_UPLOAD_SFW_BUTTON,
    NOTIFY_SEND_BUTTON,
    NOTIFY_SETTINGS_BUTTON,
)
from bot.keyboards.inline.constants import (
    BACK_TO_HOME_LABEL,
    FILE_ADMIN_CALLBACK_DATA,
    FILE_LIST_LABEL,
    FILE_SAVE_LABEL,
    MAIN_IMAGE_ADMIN_CALLBACK_DATA,
    MAIN_IMAGE_CANCEL_LABEL,
    MAIN_IMAGE_CONTINUE_UPLOAD_LABEL,
    MAIN_IMAGE_LIST_LABEL,
    MAIN_IMAGE_SCHEDULE_LABEL,
    MAIN_IMAGE_TOGGLE_NSFW_LABEL,
    MAIN_IMAGE_UPLOAD_CALLBACK_DATA,
    MAIN_IMAGE_UPLOAD_LABEL,
    NOTIFY_COMPLETE_CALLBACK_DATA,
    NOTIFY_COMPLETE_LABEL,
    NOTIFY_PREVIEW_CALLBACK_DATA,
    NOTIFY_PREVIEW_LABEL,
    NOTIFY_SETTINGS_TOGGLE_CALLBACK_DATA,
    QUIZ_ADMIN_ADD_QUICK_LABEL,
    QUIZ_ADMIN_CALLBACK_DATA,
    QUIZ_ADMIN_CATEGORY_LABEL,
    QUIZ_ADMIN_LIST_IMAGES_LABEL,
    QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA,
    QUIZ_ADMIN_LIST_MENU_LABEL,
    QUIZ_ADMIN_LIST_QUESTIONS_LABEL,
    QUIZ_ADMIN_LIST_QUIZZES_LABEL,
    QUIZ_ADMIN_SCHEDULE_MENU_LABEL,
    QUIZ_ADMIN_SCHEDULE_SET_TARGET_LABEL,
    QUIZ_ADMIN_SCHEDULE_SET_TIME_LABEL,
    QUIZ_ADMIN_SCHEDULE_TOGGLE_LABEL,
    QUIZ_ADMIN_SETTINGS_MENU_LABEL,
    QUIZ_ADMIN_SET_COOLDOWN_LABEL,
    QUIZ_ADMIN_SET_DAILY_LIMIT_LABEL,
    QUIZ_ADMIN_SET_PROBABILITY_LABEL,
    QUIZ_ADMIN_SET_TIMEOUT_LABEL,
    QUIZ_ADMIN_TEST_TRIGGER_LABEL,
    QUIZ_ADMIN_TRIGGER_LABEL,
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
        [MAIN_IMAGE_BACK_BUTTON, BACK_TO_HOME_BUTTON]
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
            InlineKeyboardButton(text=f"{page}/{total_pages} (每页{limit:02d}条)", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:list:view:{type_key}:1:{next_limit}"),
            InlineKeyboardButton(text="➡️", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:list:view:{type_key}:{next_page}:{limit}"),
        ],
        [
            InlineKeyboardButton(text="🔙 返回分类选择", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list"),
            BACK_TO_HOME_BUTTON
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_image_item_keyboard(image_id: int, is_enabled: bool) -> InlineKeyboardMarkup:
    """获取单张主图的操作键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="🗑️ 删除", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:item:delete:{image_id}"),
            InlineKeyboardButton(text="🔴 禁用" if is_enabled else "🟢 启用", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:item:toggle:{image_id}"),
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
        [NOTIFY_SETTINGS_BUTTON, NOTIFY_SEND_BUTTON],
        [BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_notification_settings_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    """获取通知设置键盘

    功能说明:
    - 列出所有配置的通知频道
    - 每个频道显示当前状态(启用/禁用), 点击可切换
    - 底部包含返回按钮

    输入参数:
    - channels: 频道配置列表, 每个元素为 dict(id, name, enabled)

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = []
    
    # 频道列表
    for ch in channels:
        name = ch.get("name", "未知频道")
        ch_id = ch.get("id")
        is_enabled = ch.get("enabled", True)
        status_icon = "🟢" if is_enabled else "🔴"
        
        btn_text = f"{status_icon} {name}"
        callback = f"{NOTIFY_SETTINGS_TOGGLE_CALLBACK_DATA}:{ch_id}"
        
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=callback)])

    # 返回按钮 (返回到通知管理面板)
    # 注意: 这里不能直接用 BACK_TO_ADMIN_PANEL_BUTTON, 因为那是返回一级面板
    # 我们需要返回到 NOTIFY_MENU (即通知面板)
    # 现有的通知面板是通过 menu.py 中的 notify_menu_handler 处理的
    # 通常我们可以复用 "admin:notify" 或者类似的 callback
    # 查看 menu.py 发现入口 callback 是 "admin:notify" (在 buttons.py 中未定义单独常量, 但在 mapping 里有)
    # 让我们假设通知面板的 callback 是 "admin:notify" (对应 NOTIFY_SEND_BUTTON 所在的面板)
    # 实际上 NOTIFY_SEND_BUTTON 是在 panel 里。
    # 让我们看 buttons.py 或 constants.py 里的定义。
    # 刚才看 buttons.py 没看到进入 notification panel 的按钮定义 (除了 NOTIFY_SEND_BUTTON 是功能按钮)
    # 等等，ADMIN_FEATURES_MAPPING 里有 "notify": (KEY_ADMIN_NOTIFY, "📢 上新通知")
    # 所以 callback 是 "admin:notify"
    
    buttons.append([InlineKeyboardButton(text="🔙 返回通知面板", callback_data="admin:notify")])
    buttons.append([BACK_TO_HOME_BUTTON])

    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(2)
    return keyboard.as_markup()


def get_quiz_image_list_pagination_keyboard(page: int, total_pages: int, limit: int) -> InlineKeyboardMarkup:
    """题图列表分页键盘"""
    builder = InlineKeyboardBuilder()

    # 上一页
    if page > 1:
        builder.button(text="⬅️ 上一页", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:image:{page - 1}:{limit}")
    else:
        builder.button(text="⛔️", callback_data="ignore")

    # 页码指示 (Toggle limit)
    next_limit = 10 if limit == 5 else (20 if limit == 10 else 5)
    builder.button(text=f"{page}/{total_pages} (每页{limit:02d}条)", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:image:1:{next_limit}")

    # 下一页
    if page < total_pages:
        builder.button(text="下一页 ➡️", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:image:{page + 1}:{limit}")
    else:
        builder.button(text="⛔️", callback_data="ignore")

    builder.adjust(3)
    
    # 返回按钮
    builder.row(
        InlineKeyboardButton(text="🔙 返回列表菜单", callback_data=QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA),
        BACK_TO_HOME_BUTTON
    )

    return builder.as_markup()


def get_quiz_image_item_keyboard(image_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """题图单项操作键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="🗑️ 删除", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:item:image:delete:{image_id}"),
            InlineKeyboardButton(text="🔴 禁用" if is_active else "🟢 启用", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:item:image:toggle:{image_id}"),
            InlineKeyboardButton(text="❌ 关闭", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:item:image:close")
        ]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_add_cancel_keyboard() -> InlineKeyboardMarkup:
    """问答快捷添加取消键盘"""
    buttons = [
        [InlineKeyboardButton(text="📝 发送示例", callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":send_example")],
        [InlineKeyboardButton(text=MAIN_IMAGE_CANCEL_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA)],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_add_success_keyboard() -> InlineKeyboardMarkup:
    """问答快捷添加成功键盘"""
    buttons = [
        [InlineKeyboardButton(text="➕ 继续添加", callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":add")],
        [BACK_TO_QUIZ_ADMIN_BUTTON, BACK_TO_HOME_BUTTON]
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


def get_main_image_schedule_cancel_keyboard() -> InlineKeyboardMarkup:
    """节日投放取消键盘 (返回投放菜单)"""
    buttons = [[InlineKeyboardButton(text=MAIN_IMAGE_CANCEL_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule")]]
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


def get_main_image_upload_success_keyboard(is_nsfw: bool) -> InlineKeyboardMarkup:
    """主图上传成功键盘 (包含继续上传)"""
    # 根据 is_nsfw 决定继续上传的类型
    upload_type = "nsfw" if is_nsfw else "sfw"
    continue_button = InlineKeyboardButton(
        text=MAIN_IMAGE_CONTINUE_UPLOAD_LABEL,
        callback_data=f"{MAIN_IMAGE_UPLOAD_CALLBACK_DATA}:{upload_type}"
    )

    buttons = [
        [continue_button],
        [MAIN_IMAGE_BACK_TO_UPLOAD_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_main_image_admin_keyboard() -> InlineKeyboardMarkup:
    """主图管理面板键盘

    功能说明:
    - 提供上传、列表、节日投放、NSFW 开关四个入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = [
        [
            InlineKeyboardButton(text=MAIN_IMAGE_UPLOAD_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload"),
            InlineKeyboardButton(text=MAIN_IMAGE_LIST_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list"),
        ],
        [
            InlineKeyboardButton(text=MAIN_IMAGE_SCHEDULE_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule"),
            InlineKeyboardButton(text=MAIN_IMAGE_TOGGLE_NSFW_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":toggle_nsfw"),
        ],
        [BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_main_image_schedule_menu_keyboard() -> InlineKeyboardMarkup:
    """获取节日投放菜单键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="🎉 创建投放", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule:create"),
            InlineKeyboardButton(text="📑 查看投放", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule:list:1:5"),
        ],
        [MAIN_IMAGE_BACK_BUTTON, BACK_TO_HOME_BUTTON]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_main_image_schedule_list_pagination_keyboard(page: int, total_pages: int, limit: int) -> InlineKeyboardMarkup:
    """获取节日投放列表分页键盘"""
    builder = InlineKeyboardBuilder()

    # 上一页
    if page > 1:
        builder.button(text="⬅️ 上一页", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:schedule:list:{page - 1}:{limit}")
    else:
        builder.button(text="⛔️", callback_data="ignore")

    # 切换每页条数
    next_limit = 10 if limit == 5 else (20 if limit == 10 else 5)
    builder.button(text=f"{page}/{total_pages} (每页{limit:02d}条)", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:schedule:list:1:{next_limit}")

    # 下一页
    if page < total_pages:
        builder.button(text="下一页 ➡️", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:schedule:list:{page + 1}:{limit}")
    else:
        builder.button(text="⛔️", callback_data="ignore")

    builder.adjust(3)

    builder.row(
        InlineKeyboardButton(text="🔙 返回投放菜单", callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule"),
        InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data=MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule:back_home")
    )
    return builder.as_markup()


def get_main_image_schedule_item_keyboard(schedule_id: int) -> InlineKeyboardMarkup:
    """获取单条投放记录的操作键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="🗑️ 删除", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:schedule:item:delete:{schedule_id}"),
            InlineKeyboardButton(text="❌ 关闭", callback_data=f"{MAIN_IMAGE_ADMIN_CALLBACK_DATA}:schedule:item:close"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_files_admin_keyboard() -> InlineKeyboardMarkup:
    """文件管理面板键盘

    功能说明:
    - 提供保存文件与查看文件两个入口
    - 底部包含返回管理员面板与返回主页

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = [
        [
            InlineKeyboardButton(text=FILE_SAVE_LABEL, callback_data=FILE_ADMIN_CALLBACK_DATA + ":save"),
            InlineKeyboardButton(text=FILE_LIST_LABEL, callback_data=FILE_ADMIN_CALLBACK_DATA + ":list:1:5"),
        ],
        [BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_files_list_pagination_keyboard(page: int, total_pages: int, limit: int) -> InlineKeyboardMarkup:
    """文件列表分页键盘

    输入参数:
    - page: 当前页码
    - total_pages: 总页数
    - limit: 每页条数

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    prev_page = max(1, page - 1)
    next_page = min(total_pages, page + 1)
    next_limit = 10 if limit == 5 else (20 if limit == 10 else 5)

    buttons = [
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"{FILE_ADMIN_CALLBACK_DATA}:list:{prev_page}:{limit}"),
            InlineKeyboardButton(text=f"{page}/{total_pages} (每页{limit:02d}条)", callback_data=f"{FILE_ADMIN_CALLBACK_DATA}:list:1:{next_limit}"),
            InlineKeyboardButton(text="➡️", callback_data=f"{FILE_ADMIN_CALLBACK_DATA}:list:{next_page}:{limit}"),
        ],
        [
            InlineKeyboardButton(text="🔙 返回文件管理", callback_data=FILE_ADMIN_CALLBACK_DATA),
            InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data=f"{FILE_ADMIN_CALLBACK_DATA}:back_home"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_files_cancel_keyboard() -> InlineKeyboardMarkup:
    """文件管理取消键盘

    功能说明:
    - 提供取消按钮, 点击后返回文件管理主面板

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = [[InlineKeyboardButton(text=MAIN_IMAGE_CANCEL_LABEL, callback_data=FILE_ADMIN_CALLBACK_DATA)]]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_files_save_success_keyboard() -> InlineKeyboardMarkup:
    """文件保存成功键盘

    功能说明:
    - 第一行: 继续保存 (保持在当前状态)
    - 第二行: 返回文件管理, 返回主页

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = [
        [
            InlineKeyboardButton(text="📥 继续保存", callback_data=f"{FILE_ADMIN_CALLBACK_DATA}:save"),
        ],
        [
            InlineKeyboardButton(text="🔙 返回文件管理", callback_data=FILE_ADMIN_CALLBACK_DATA),
            BACK_TO_HOME_BUTTON,
        ],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_files_item_keyboard(file_record_id: int) -> InlineKeyboardMarkup:
    """文件项操作键盘

    功能说明:
    - 提供删除与关闭操作

    输入参数:
    - file_record_id: 记录ID

    返回值:
    - InlineKeyboardMarkup: 键盘对象
    """
    buttons = [
        [
            InlineKeyboardButton(text="🗑️ 删除", callback_data=f"{FILE_ADMIN_CALLBACK_DATA}:item:delete:{file_record_id}"),
            InlineKeyboardButton(text="❌ 关闭", callback_data=f"{FILE_ADMIN_CALLBACK_DATA}:item:close"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_quiz_admin_keyboard(is_global_enabled: bool = True) -> InlineKeyboardMarkup:
    """问答管理菜单键盘"""
    toggle_text = "🟢 总开关: 开启" if is_global_enabled else "🔴 总开关: 关闭"
    
    buttons = [
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_ADD_QUICK_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":add"),
            InlineKeyboardButton(text=QUIZ_ADMIN_TRIGGER_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":trigger")
        ],
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_LIST_MENU_LABEL, callback_data=QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA),
            InlineKeyboardButton(text=QUIZ_ADMIN_CATEGORY_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":category")
        ],
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_TEST_TRIGGER_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":test_trigger"),
            InlineKeyboardButton(text=toggle_text, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":toggle_global")
        ],
        [BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_list_keyboard() -> InlineKeyboardMarkup:
    """问答列表菜单键盘"""
    buttons = [
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_LIST_QUESTIONS_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":list:view:question:1:5"),
            InlineKeyboardButton(text=QUIZ_ADMIN_LIST_IMAGES_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":list:view:image:1:5"),
            InlineKeyboardButton(text=QUIZ_ADMIN_LIST_QUIZZES_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":list:view:quiz:1:5")
        ],
        [BACK_TO_QUIZ_ADMIN_BUTTON, BACK_TO_HOME_BUTTON]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_question_list_pagination_keyboard(page: int, total_pages: int, limit: int) -> InlineKeyboardMarkup:
    """题目列表分页键盘"""
    builder = InlineKeyboardBuilder()

    # 上一页
    if page > 1:
        builder.button(text="⬅️ 上一页", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:question:{page - 1}:{limit}")
    else:
        builder.button(text="⛔️", callback_data="ignore")

    # 页码指示 (Toggle limit)
    next_limit = 10 if limit == 5 else (20 if limit == 10 else 5)
    builder.button(text=f"{page}/{total_pages} (每页{limit:02d}条)", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:question:1:{next_limit}")

    # 下一页
    if page < total_pages:
        builder.button(text="下一页 ➡️", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:list:view:question:{page + 1}:{limit}")
    else:
        builder.button(text="⛔️", callback_data="ignore")

    builder.adjust(3)
    
    # 返回按钮
    builder.row(
        InlineKeyboardButton(text="🔙 返回列表菜单", callback_data=QUIZ_ADMIN_LIST_MENU_CALLBACK_DATA),
        BACK_TO_HOME_BUTTON
    )

    return builder.as_markup()


def get_quiz_question_item_keyboard(question_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """题目单项操作键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="🗑️ 删除", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:item:question:delete:{question_id}"),
            InlineKeyboardButton(text="🔴 禁用" if is_active else "🟢 启用", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:item:question:toggle:{question_id}"),
            InlineKeyboardButton(text="❌ 关闭", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:item:question:close")
        ]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_trigger_keyboard() -> InlineKeyboardMarkup:
    """问答触发设置主菜单键盘"""
    buttons = [
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_SETTINGS_MENU_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":settings_menu"),
            InlineKeyboardButton(text=QUIZ_ADMIN_SCHEDULE_MENU_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":schedule_menu")
        ],
        [BACK_TO_QUIZ_ADMIN_BUTTON, BACK_TO_HOME_BUTTON]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_settings_selection_keyboard() -> InlineKeyboardMarkup:
    """问答基础参数设置选择键盘"""
    buttons = [
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_PROBABILITY_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":set:probability"),
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_COOLDOWN_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":set:cooldown")
        ],
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_DAILY_LIMIT_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":set:daily_limit"),
            InlineKeyboardButton(text=QUIZ_ADMIN_SET_TIMEOUT_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":set:timeout")
        ],
        [
            InlineKeyboardButton(text="🔙 返回触发设置", callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":trigger"),
            BACK_TO_HOME_BUTTON
        ]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_schedule_keyboard(is_enabled: bool = False) -> InlineKeyboardMarkup:
    """问答定时触发设置键盘"""
    toggle_text = "🟢 定时开关: 开启" if is_enabled else "🔴 定时开关: 关闭"
    
    buttons = [
        [
            InlineKeyboardButton(text=QUIZ_ADMIN_SCHEDULE_SET_TIME_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":schedule:set_time"),
            InlineKeyboardButton(text=QUIZ_ADMIN_SCHEDULE_SET_TARGET_LABEL, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":schedule:set_target")
        ],
        [
            InlineKeyboardButton(text=toggle_text, callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":schedule:toggle")
        ],
        [
            InlineKeyboardButton(text="🔙 返回触发设置", callback_data=QUIZ_ADMIN_CALLBACK_DATA + ":trigger"),
            BACK_TO_HOME_BUTTON
        ]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()

def get_quiz_category_list_keyboard(categories: list) -> InlineKeyboardMarkup:
    """问答分类列表键盘"""
    builder = InlineKeyboardBuilder()

    # 列表按钮
    for cat in categories:
        builder.button(
            text=f"{cat.id}. {cat.name} ({'🟢' if cat.is_active else '🔴'})",
            callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:cat:view:{cat.id}"
        )
    builder.adjust(2) # 每行2个

    # 功能按钮
    builder.row(
        InlineKeyboardButton(text="➕ 添加分类", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:cat:add")
    )

    # 返回按钮
    builder.row(BACK_TO_QUIZ_ADMIN_BUTTON, BACK_TO_HOME_BUTTON)

    return builder.as_markup()


def get_quiz_category_item_keyboard(category_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """问答分类详情键盘"""
    buttons = [
        [
            InlineKeyboardButton(text="✏️ 修改名称", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:cat:edit:{category_id}"),
            InlineKeyboardButton(text="🔴 禁用" if is_active else "🟢 启用", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:cat:toggle:{category_id}")
        ],
        [
             InlineKeyboardButton(text="🗑️ 删除", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:cat:delete:{category_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 返回列表", callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:category"),
            BACK_TO_HOME_BUTTON
        ]
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()


def get_quiz_category_cancel_keyboard() -> InlineKeyboardMarkup:
    """分类编辑取消键盘"""
    buttons = [[InlineKeyboardButton(text=MAIN_IMAGE_CANCEL_LABEL, callback_data=f"{QUIZ_ADMIN_CALLBACK_DATA}:category")]]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    return keyboard.as_markup()
