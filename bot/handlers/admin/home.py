from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.admin import get_admin_panel_keyboard
from bot.keyboards.inline.constants import ADMIN_PANEL_LABEL
from bot.services.config_service import list_admin_features
from bot.services.main_message import MainMessageService
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
    features = await list_admin_features(session)
    kb = get_admin_panel_keyboard(features)
    user_id = callback.from_user.id if callback.from_user else None
    await _resolve_role(session, user_id)

    await main_msg.update_on_callback(callback, f"*{ADMIN_PANEL_LABEL}*", kb)
    await callback.answer()

