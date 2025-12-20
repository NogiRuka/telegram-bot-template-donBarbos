from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.start import get_common_image
from bot.keyboards.inline.constants import ADMIN_PERMS_PANEL_LABEL
from bot.keyboards.inline.owner import get_admin_perms_panel_keyboard
from bot.services.config_service import (
    ADMIN_PERMISSIONS_MAPPING,
    list_admin_permissions,
    toggle_config,
)
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_owner

router = Router(name="owner_admin_features")


@router.callback_query(F.data == "owner:admin_perms")
@require_owner
async def show_admin_perms_panel(
    callback: CallbackQuery, 
    session: AsyncSession, 
    main_msg: MainMessageService
) -> None:
    """展示管理员功能面板

    功能说明:
    - 显示管理员功能开关列表, 支持返回上一级与返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    perms = await list_admin_permissions(session)
    kb = get_admin_perms_panel_keyboard(perms)
    image = get_common_image()
    
    await main_msg.update_on_callback(callback, ADMIN_PERMS_PANEL_LABEL, kb, image_path=image)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("owner:admin_perms:toggle:"))
@require_owner
async def toggle_admin_permissions(
    callback: CallbackQuery, 
    session: AsyncSession, 
    main_msg: MainMessageService
) -> None:
    """统一切换管理员功能开关

    功能说明:
    - 处理 `owner:admin_perms:toggle:*` 的所有管理员功能开关, 统一翻转配置并刷新功能面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    try:
        parts = (callback.data or "").split(":")
        key = parts[-1] if len(parts) >= 4 else ""
        
        if key not in ADMIN_PERMISSIONS_MAPPING:
            await callback.answer("🔴 无效的权限项", show_alert=True)
            return
            
        config_key, label = ADMIN_PERMISSIONS_MAPPING[key]
        operator_id = callback.from_user.id if getattr(callback, "from_user", None) else None
        new_val = await toggle_config(session, config_key, operator_id=operator_id)
        perms = await list_admin_permissions(session)
        
        await main_msg.update_on_callback(
            callback, 
            ADMIN_PERMS_PANEL_LABEL, 
            get_admin_perms_panel_keyboard(perms),
            image_path=get_common_image()
        )
        await callback.answer(f"{'🟢' if new_val else '🔴'} {label}: {'启用' if new_val else '禁用'}")
    except Exception:
        await callback.answer("🔴 操作失败，请稍后重试", show_alert=True)

