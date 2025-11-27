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
        [InlineKeyboardButton(text="👮 管理员管理", callback_data="owner:admins")],
        [InlineKeyboardButton(text="🧩 功能开关", callback_data="owner:features")],
        [InlineKeyboardButton(text="🛡️ 管理员权限", callback_data="owner:admin_perms")],
        [InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back")],
    ]
    kb = InlineKeyboardBuilder(markup=buttons)
    kb.adjust(1)
    return kb.as_markup()


def get_features_panel_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """功能开关面板键盘

    功能说明:
    - 控制用户功能的开关, 使用状态 emoji (✅/❌) 清晰显示开启关闭
    - 底部包含返回上一级与返回主面板按钮

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 功能开关键盘
    """
    def status(v: bool) -> str:
        return "✅" if v else "❌"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text=f"🧲 用户总开关 {status(features.get('user.features.enabled', False))}",
        callback_data="owner:features:toggle:user_all",
    ))
    kb.row(InlineKeyboardButton(
        text=f"🤖 机器人开关 {status(features.get('bot.features.enabled', False))}",
        callback_data="owner:features:toggle:bot_all",
    ))
    kb.row(InlineKeyboardButton(
        text=f"🎬 用户注册 {status(features.get('user.register', False))}",
        callback_data="owner:features:toggle:user_register",
    ))
    kb.row(InlineKeyboardButton(
        text=f"👤 账号信息 {status(features.get('user.info', False))}",
        callback_data="owner:features:toggle:user_info",
    ))
    kb.row(InlineKeyboardButton(
        text=f"🔐 修改密码 {status(features.get('user.password', False))}",
        callback_data="owner:features:toggle:user_password",
    ))
    kb.row(InlineKeyboardButton(
        text=f"🛰️ 线路信息 {status(features.get('user.lines', False))}",
        callback_data="owner:features:toggle:user_lines",
    ))
    kb.row(InlineKeyboardButton(
        text=f"📱 设备管理 {status(features.get('user.devices', False))}",
        callback_data="owner:features:toggle:user_devices",
    ))
    kb.row(InlineKeyboardButton(
        text=f"📤 导出用户 {status(features.get('user.export_users', False))}",
        callback_data="owner:features:toggle:user_export_users",
    ))
    kb.row(
        InlineKeyboardButton(text="↩️ 返回上一级", callback_data="owner:panel"),
        InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"),
    )
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
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="👀 查看管理员列表", callback_data="owner:admins:list"))
    kb.row(
        InlineKeyboardButton(text="↩️ 返回上一级", callback_data="owner:panel"),
        InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"),
    )
    return kb.as_markup()


def get_admin_perms_panel_keyboard(perms: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员权限面板键盘

    功能说明:
    - 控制管理员可使用的功能权限开关, 状态使用 emoji (✅/❌) 显示
    - 底部包含返回上一级与返回主面板按钮

    输入参数:
    - perms: 管理员权限映射

    返回值:
    - InlineKeyboardMarkup: 管理员权限面板键盘
    """
    def status(v: bool) -> str:
        return "✅" if v else "❌"
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(
        text=f"🧲 管理员总开关 {status(perms.get('admin.features.enabled', False))}",
        callback_data="owner:admin_perms:toggle:features",
    ))
    kb.row(InlineKeyboardButton(
        text=f"👥 群组管理 {status(perms.get('admin.permissions.groups', False))}",
        callback_data="owner:admin_perms:toggle:groups",
    ))
    kb.row(InlineKeyboardButton(
        text=f"📊 统计数据 {status(perms.get('admin.permissions.stats', False))}",
        callback_data="owner:admin_perms:toggle:stats",
    ))
    kb.row(InlineKeyboardButton(
        text=f"🛂 开放注册 {status(perms.get('admin.permissions.open_registration', False))}",
        callback_data="owner:admin_perms:toggle:open_registration",
    ))
    kb.row(
        InlineKeyboardButton(text="↩️ 返回上一级", callback_data="owner:panel"),
        InlineKeyboardButton(text="🏠 返回主面板", callback_data="home:back"),
    )
    return kb.as_markup()
