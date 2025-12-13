from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.start_admin import get_admin_panel_keyboard
from bot.services.config_service import list_admin_permissions
from bot.services.main_message import MainMessageService
from bot.utils.images import get_common_image
from bot.utils.permissions import _resolve_role, require_admin_priv

router = Router(name="admin_home")


@router.callback_query(F.data == "admin:panel")
@require_admin_priv
async def show_admin_panel(
    callback: CallbackQuery, 
    session: AsyncSession, 
    main_msg: MainMessageService
) -> None:
    """展示管理员面板

    功能说明:
    - 展示二级管理员面板菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    perms = await list_admin_permissions(session)
    kb = get_admin_panel_keyboard(perms)
    user_id = callback.from_user.id if callback.from_user else None
    await _resolve_role(session, user_id)
    image = get_common_image()
    caption = "🛡️ 管理员面板"
    
    await main_msg.update_on_callback(callback, caption, kb, image_path=image)
    await callback.answer()

