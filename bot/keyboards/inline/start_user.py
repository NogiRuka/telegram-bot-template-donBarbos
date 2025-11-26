from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_user_keyboard() -> InlineKeyboardMarkup:
    """用户首页键盘

    功能说明:
    - 提供一级入口: 个人信息与账号中心

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [InlineKeyboardButton(text="👤 个人信息", callback_data="start:profile")],
        [InlineKeyboardButton(text="🧾 账号中心", callback_data="start:account")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()


def get_account_center_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """账号中心键盘

    功能说明:
    - 二级入口: 包含与账号相关功能, 底部包含返回主面板

    输入参数:
    - features: 功能开关映射

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📤 消息导出", callback_data="start:export"))
    if features.get("features_enabled", False) and features.get("feature_emby_register", False):
        builder.row(InlineKeyboardButton(text="🎬 Emby 注册", callback_data="emby:register"))
    builder.row(InlineKeyboardButton(text="↩️ 返回主面板", callback_data="home:back"))
    return builder.as_markup()

