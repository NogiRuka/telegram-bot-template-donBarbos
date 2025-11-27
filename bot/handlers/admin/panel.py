from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_admin import get_admin_panel_keyboard
from bot.services.config_service import list_admin_permissions
from bot.utils.permissions import _resolve_role, require_admin_feature, require_admin_priv

router = Router(name="admin_panel")


@router.callback_query(F.data == "admin:panel")
@require_admin_priv
async def show_admin_panel(callback: CallbackQuery, session: AsyncSession) -> None:
    """展示管理员面板

    功能说明:
    - 展示二级管理员面板菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    perms = await list_admin_permissions(session)
    kb = get_admin_panel_keyboard(perms)
    user_id = callback.from_user.id if callback.from_user else None
    await _resolve_role(session, user_id)
    image = get_common_image()
    caption = "🛡️ 管理员面板"
    if callback.message:
        await render_view(callback.message, image, caption, kb)
    await callback.answer()


@router.callback_query(F.data == "admin:groups")
@require_admin_priv
@require_admin_feature("admin.groups")
async def open_groups_feature(callback: CallbackQuery, _session: AsyncSession) -> None:
    """打开群组管理功能

    功能说明:
    - 管理员面板中的群组管理入口占位处理, 功能关闭时提示不可用

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await callback.answer("功能建设中, 请使用 /admin_groups 命令", show_alert=True)


@router.callback_query(F.data == "admin:stats")
@require_admin_priv
@require_admin_feature("admin.stats")
async def open_stats_feature(callback: CallbackQuery, _session: AsyncSession) -> None:
    """打开统计数据功能

    功能说明:
    - 管理员面板中的统计数据入口占位处理, 功能关闭时提示不可用

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await callback.answer("功能建设中, 请使用 /admin_stats 命令", show_alert=True)


@router.callback_query(F.data == "admin:open_registration")
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def open_registration_feature(callback: CallbackQuery, _session: AsyncSession) -> None:
    """打开开放注册功能

    功能说明:
    - 管理员面板中的开放注册入口占位处理, 功能关闭时提示不可用

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await callback.answer("功能建设中", show_alert=True)
