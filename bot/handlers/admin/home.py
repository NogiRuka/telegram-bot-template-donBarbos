from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.images import get_common_image
from bot.keyboards.inline.start_admin import get_admin_panel_keyboard
from bot.services.config_service import list_admin_permissions
from bot.utils.permissions import _resolve_role, require_admin_priv
from bot.utils.view import render_view

router = Router(name="admin_home")


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
    msg = callback.message
    if isinstance(msg, types.Message):
        await render_view(msg, image, caption, kb)
    await callback.answer()

