from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_admin import get_admin_panel_keyboard
from bot.services.config_service import list_admin_permissions, list_features
from bot.utils.permissions import _resolve_role, require_admin_priv

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
    features = await list_features(session)
    perms = await list_admin_permissions(session)
    kb = get_admin_panel_keyboard(features, perms)
    user_id = callback.from_user.id if callback.from_user else None
    await _resolve_role(session, user_id)
    image = get_common_image()
    caption = "🛡️ 管理员面板"
    if callback.message:
        await render_view(callback.message, image, caption, kb)
    await callback.answer()
