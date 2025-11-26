from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.inline.start_admin import build_admin_home_rows
from bot.keyboards.inline.start_user import make_home_keyboard


def get_start_owner_keyboard() -> InlineKeyboardMarkup:
    """所有者首页键盘

    功能说明:
    - 复用管理员首页并追加所有者面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 内联键盘
    """
    rows = build_admin_home_rows()
    rows.append([InlineKeyboardButton(text="👑 所有者面板", callback_data="owner:panel")])
    return make_home_keyboard(rows)


def get_owner_panel_keyboard() -> InlineKeyboardMarkup:
    """所有者面板键盘

    功能说明:
    - 提供所有者面板主入口, 包含总开关、功能开关、管理员管理与返回主面板

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 面板主键盘
    """
    buttons = [
        [InlineKeyboardButton(text="🚦 机器人总开关", callback_data="owner:toggle:bot")],
        [InlineKeyboardButton(text="🧩 功能开关", callback_data="owner:features")],
        [InlineKeyboardButton(text="👮 管理员管理", callback_data="owner:admins")],
        [InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()


def get_features_panel_keyboard() -> InlineKeyboardMarkup:
    """功能开关面板键盘

    功能说明:
    - 提供总功能开关与示例子功能开关, 以及返回所有者主面板

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 功能开关键盘
    """
    btn_toggle_all = InlineKeyboardButton(
        text="🧲 切换全部功能",
        callback_data="owner:features:toggle:all",
    )
    btn_toggle_emby = InlineKeyboardButton(
        text="🎬 切换 Emby 注册",
        callback_data="owner:features:toggle:emby_register",
    )
    btn_toggle_admin_open = InlineKeyboardButton(
        text="🛂 切换管理员开放注册权限",
        callback_data="owner:features:toggle:admin_open_registration",
    )
    btn_toggle_export = InlineKeyboardButton(
        text="📤 切换导出用户",
        callback_data="owner:features:toggle:export_users",
    )
    btn_back = InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back")
    buttons = [
        [btn_toggle_all],
        [btn_toggle_emby],
        [btn_toggle_admin_open],
        [btn_toggle_export],
        [btn_back],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()


def get_admins_panel_keyboard() -> InlineKeyboardMarkup:
    """管理员管理面板键盘

    功能说明:
    - 提供查看管理员列表与返回所有者主面板入口

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 管理员面板键盘
    """
    buttons = [
        [InlineKeyboardButton(text="👀 查看管理员列表", callback_data="owner:admins:list")],
        [InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()
