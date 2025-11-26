
import contextlib

from aiogram import Router, types
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.handlers.menu import render_view
from bot.keyboards.inline.start_admin import get_admin_panel_keyboard, get_start_admin_keyboard
from bot.keyboards.inline.start_owner import get_start_owner_keyboard
from bot.keyboards.inline.start_user import get_account_center_keyboard, get_start_user_keyboard
from bot.services.analytics import analytics
from bot.services.config_service import list_features
from bot.utils.permissions import require_admin_priv

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


# 移除本地首页键盘构建函数, 统一复用键盘模块的构建函数


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
    with contextlib.suppress(Exception):
        if session is not None:
            await list_features(session)

    if role == "owner":
        kb = get_start_owner_keyboard()
        caption = "🌸 所有者欢迎页"
        image = "assets/ui/start_owner.jpg"
    elif role == "admin":
        kb = get_start_admin_keyboard()
        caption = "🌸 管理员欢迎页"
        image = "assets/ui/start_admin.jpg"
    else:
        kb = get_start_user_keyboard()
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


@router.callback_query(lambda c: c.data == "home:back")
async def back_to_home(callback: types.CallbackQuery, session: AsyncSession, role: str) -> None:
    """返回主面板

    功能说明:
    - 根据用户角色返回至对应的一级主页键盘

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - role: 用户角色标识

    返回值:
    - None
    """
    with contextlib.suppress(Exception):
        await list_features(session)
    caption = "🌸 欢迎使用机器人!"
    image = "assets/ui/start_user.jpg"
    kb = get_start_user_keyboard()
    if role == "admin":
        caption = "🌸 管理员欢迎页"
        image = "assets/ui/start_admin.jpg"
        kb = get_start_admin_keyboard()
    elif role == "owner":
        caption = "🌸 所有者欢迎页"
        image = "assets/ui/start_owner.jpg"
        kb = get_start_owner_keyboard()
    if callback.message:
        await render_view(callback.message, image, caption, kb)
    await callback.answer()


@router.callback_query(lambda c: c.data == "start:account")
async def show_account_center(callback: types.CallbackQuery, session: AsyncSession) -> None:
    """展示账号中心

    功能说明:
    - 展示二级账号中心菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    features = await list_features(session)
    kb = get_account_center_keyboard(features)
    if callback.message:
        await render_view(callback.message, "assets/ui/start_user.jpg", "🧾 账号中心", kb)
    await callback.answer()


@router.callback_query(lambda c: c.data == "admin:panel")
@require_admin_priv
async def show_admin_panel(callback: types.CallbackQuery, session: AsyncSession, role: str) -> None:
    """展示管理员面板

    功能说明:
    - 展示二级管理员面板菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - role: 用户角色标识

    返回值:
    - None
    """
    features = await list_features(session)
    kb = get_admin_panel_keyboard(features)
    image = "assets/ui/start_admin.jpg" if role == "admin" else "assets/ui/start_owner.jpg"
    caption = "🛡️ 管理员面板"
    if callback.message:
        await render_view(callback.message, image, caption, kb)
    await callback.answer()
