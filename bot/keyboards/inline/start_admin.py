from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_start_admin_keyboard() -> InlineKeyboardMarkup:
    """管理员首页键盘

    功能说明:
    - 复用用户首页并追加管理员面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    buttons = [
        [InlineKeyboardButton(text="👤 个人信息", callback_data="start:profile")],
        [InlineKeyboardButton(text="🧾 账号中心", callback_data="start:account")],
        [InlineKeyboardButton(text="🛡️ 管理员面板", callback_data="admin:panel")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()


def get_admin_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员面板键盘

    功能说明:
    - 二级入口: 管理功能集合, 底部包含返回主面板

    输入参数:
    - features: 功能开关映射

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 群组管理", callback_data="start:groups"))
    builder.row(InlineKeyboardButton(text="📈 统计数据", callback_data="start:stats"))
    if features.get("features_enabled", False) and features.get("feature_admin_open_registration", False):
        builder.row(InlineKeyboardButton(text="🛂 开放注册", callback_data="admin:open_registration"))
    builder.row(InlineKeyboardButton(text="↩️ 返回主面板", callback_data="home:back"))
    return builder.as_markup()

