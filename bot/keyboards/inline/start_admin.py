from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.start_user import build_user_home_rows, make_home_keyboard


def build_admin_home_rows() -> list[list[InlineKeyboardButton]]:
    """管理员首页行构建

    功能说明:
    - 在用户基础首页按钮行上追加管理员面板入口

    输入参数:
    - 无

    返回值:
    - list[list[InlineKeyboardButton]]: 按钮行集合
    """
    rows = build_user_home_rows()
    rows.append([InlineKeyboardButton(text="🛡️ 管理员面板", callback_data="admin:panel")])
    return rows


def get_start_admin_keyboard() -> InlineKeyboardMarkup:
    """管理员首页键盘

    功能说明:
    - 复用用户首页并追加管理员面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    return make_home_keyboard(build_admin_home_rows())


def get_admin_panel_keyboard(features: dict[str, bool], perms: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员面板键盘

    功能说明:
    - 二级入口: 管理功能集合, 底部包含返回主面板

    输入参数:
    - features: 功能开关映射

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    builder = InlineKeyboardBuilder()
    if perms.get("admin_perm_groups", False):
        builder.row(InlineKeyboardButton(text="👥 群组管理", callback_data="start:groups"))
    if perms.get("admin_perm_stats", False):
        builder.row(InlineKeyboardButton(text="📊 统计数据", callback_data="start:stats"))
    if (
        perms.get("admin_perm_open_registration", False)
        and features.get("features_enabled", False)
        and features.get("feature_admin_open_registration", False)
    ):
        builder.row(InlineKeyboardButton(text="🛂 开放注册", callback_data="admin:open_registration"))
    builder.row(InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"))
    return builder.as_markup()
