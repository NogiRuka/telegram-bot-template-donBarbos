
import contextlib

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.handlers.menu import render_view
from bot.services.analytics import analytics
from bot.services.config_service import list_features

router = Router(name="start")


def determine_role(user_id: int) -> str:
    """角色判定

    功能说明:
    - 基于配置判断角色, 返回 "owner" | "admin" | "user"

    输入参数:
    - user_id: Telegram 用户ID

    返回值:
    - str: 角色标识
    """
    with contextlib.suppress(Exception):
        if user_id == settings.get_owner_id():
            return "owner"
        if user_id in set(settings.get_admin_ids()):
            return "admin"
    return "user"


def build_owner_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """所有者首页键盘构建

    功能说明:
    - 根据功能开关构建所有者首页按钮

    输入参数:
    - features: 功能开关映射

    返回值:
    - InlineKeyboardMarkup: 键盘
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 管理面板", callback_data="panel:main"))
    builder.row(InlineKeyboardButton(text="📊 群组管理", callback_data="start:groups"))
    builder.row(InlineKeyboardButton(text="📈 统计数据", callback_data="start:stats"))
    if features.get("features_enabled", False) and features.get("feature_emby_register", False):
        builder.row(InlineKeyboardButton(text="🎬 Emby 注册", callback_data="emby:register"))
    builder.row(InlineKeyboardButton(text="🆘 支持", callback_data="start:support"))
    return builder.as_markup()


def build_admin_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """管理员首页键盘构建

    功能说明:
    - 根据功能开关构建管理员首页按钮

    输入参数:
    - features: 功能开关映射

    返回值:
    - InlineKeyboardMarkup: 键盘
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 个人信息", callback_data="start:profile"))
    builder.row(InlineKeyboardButton(text="📊 群组管理", callback_data="start:groups"))
    builder.row(InlineKeyboardButton(text="📈 统计数据", callback_data="start:stats"))
    if features.get("features_enabled", False) and features.get("feature_admin_open_registration", False):
        builder.row(InlineKeyboardButton(text="🛂 开放注册", callback_data="admin:open_registration"))
    builder.row(InlineKeyboardButton(text="🆘 支持", callback_data="start:support"))
    return builder.as_markup()


def build_user_keyboard(features: dict[str, bool]) -> InlineKeyboardMarkup:
    """用户首页键盘构建

    功能说明:
    - 根据功能开关构建用户首页按钮

    输入参数:
    - features: 功能开关映射

    返回值:
    - InlineKeyboardMarkup: 键盘
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 个人信息", callback_data="start:profile"))
    if features.get("features_enabled", False) and features.get("feature_emby_register", False):
        builder.row(InlineKeyboardButton(text="🎬 Emby 注册", callback_data="emby:register"))
    builder.row(InlineKeyboardButton(text="📤 消息导出", callback_data="start:export"))
    builder.row(InlineKeyboardButton(text="🆘 支持", callback_data="start:support"))
    return builder.as_markup()


@router.message(CommandStart())
@analytics.track_event("Sign Up")
async def start_handler(message: types.Message, role: str | None = None, session: AsyncSession | None = None) -> None:
    """欢迎消息处理器

    功能说明:
    - 根据角色显示不同首页界面与按钮

    输入参数:
    - message: Telegram消息对象
    - role: 用户角色标识

    返回值:
    - None
    """
    image = "assets/ui/start_user.jpg"
    if role is None:
        user = message.from_user
        uid = user.id if user else None
        role = determine_role(uid) if uid else "user"
    features: dict[str, bool] = {}
    with contextlib.suppress(Exception):
        if session is not None:
            features = await list_features(session)

    if role == "owner":
        kb = build_owner_keyboard(features)
        caption = "🌸 所有者欢迎页"
        image = "assets/ui/start_owner.jpg"
    elif role == "admin":
        kb = build_admin_keyboard(features)
        caption = "🌸 管理员欢迎页"
        image = "assets/ui/start_admin.jpg"
    else:
        kb = build_user_keyboard(features)
        caption = "🌸 欢迎使用机器人!"
    await render_view(message, image, caption, kb)


@router.callback_query(lambda c: c.data in {"emby:register", "admin:open_registration"})
async def placeholder_callbacks(callback: types.CallbackQuery) -> None:
    """占位回调处理器

    功能说明:
    - 处理尚未实现的功能入口, 避免点击按钮无响应

    输入参数:
    - callback: 回调对象

    返回值:
    - None
    """
    with contextlib.suppress(Exception):
        await callback.answer("功能建设中, 请稍后再试", show_alert=True)
