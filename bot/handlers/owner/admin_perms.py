from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_owner import get_admin_perms_panel_keyboard
from bot.services.config_service import list_admin_permissions, toggle_config
from bot.utils.permissions import require_owner
from bot.utils.view import render_view

router = Router(name="owner_admin_perms")


@router.callback_query(F.data == "owner:admin_perms")
@require_owner
async def show_admin_perms_panel(callback: CallbackQuery, session: AsyncSession) -> None:
    """展示管理员权限面板

    功能说明:
    - 显示管理员权限开关列表, 支持返回上一级与返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    perms = await list_admin_permissions(session)
    kb = get_admin_perms_panel_keyboard(perms)
    msg = callback.message
    if isinstance(msg, types.Message):
        image = get_common_image()
        await render_view(msg, image, "🛡️ 管理员权限", kb)
    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("owner:admin_perms:toggle:"))
@require_owner
async def toggle_admin_permissions(callback: CallbackQuery, session: AsyncSession) -> None:
    """统一切换管理员权限开关

    功能说明:
    - 处理 `owner:admin_perms:toggle:*` 的所有管理员权限开关, 统一翻转配置并刷新权限面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        parts = (callback.data or "").split(":")
        key = parts[-1] if len(parts) >= 4 else ""
        mapping: dict[str, tuple[str, str]] = {
            "features": ("admin.features.enabled", "管理员总开关"),
            "groups": ("admin.groups", "群组管理"),
            "stats": ("admin.stats", "统计数据"),
            "open_registration": ("admin.open_registration", "开放注册"),
            "hitokoto": ("admin.hitokoto", "一言管理"),
            "new_item_notification": ("admin.new_item_notification", "新片通知"),
        }
        if key not in mapping:
            await callback.answer("🔴 无效的权限项", show_alert=True)
            return
        config_key, label = mapping[key]
        operator_id = callback.from_user.id if getattr(callback, "from_user", None) else None
        new_val = await toggle_config(session, config_key, operator_id=operator_id)
        perms = await list_admin_permissions(session)
        msg = callback.message
        if isinstance(msg, types.Message):
            await render_view(msg, get_common_image(), "🛡️ 管理员权限", get_admin_perms_panel_keyboard(perms))
        await callback.answer(f"{'🟢' if new_val else '🔴'} {label}: {'启用' if new_val else '禁用'}")
    except Exception:
        await callback.answer("🔴 操作失败，请稍后重试", show_alert=True)

