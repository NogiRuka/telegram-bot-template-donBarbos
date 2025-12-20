from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.buttons import *
from bot.keyboards.inline.constants import (
    BACK_TO_HOME_LABEL,
    NOTIFY_COMPLETE_CALLBACK_DATA,
    NOTIFY_COMPLETE_LABEL,
    NOTIFY_PREVIEW_CALLBACK_DATA,
    NOTIFY_PREVIEW_LABEL,
    NOTIFY_SEND_CALLBACK_DATA,
    NOTIFY_SEND_LABEL,
)


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
            InlineKeyboardButton(text=f"{NOTIFY_COMPLETE_LABEL} ({pending_completion})", callback_data=NOTIFY_COMPLETE_CALLBACK_DATA),
            InlineKeyboardButton(text=f"{NOTIFY_PREVIEW_LABEL} ({pending_review})", callback_data=NOTIFY_PREVIEW_CALLBACK_DATA),
            InlineKeyboardButton(text=NOTIFY_SEND_LABEL, callback_data=NOTIFY_SEND_CALLBACK_DATA),
        ],
        [BACK_TO_ADMIN_PANEL_BUTTON],
        [BACK_TO_HOME_BUTTON],
    ]
    keyboard = InlineKeyboardBuilder(markup=buttons)
    # 第一行3个功能键, 后两行各1个导航键
    keyboard.adjust(3, 2)
    return keyboard.as_markup()
