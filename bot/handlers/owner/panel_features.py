from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_owner import get_admin_perms_panel_keyboard, get_features_panel_keyboard
from bot.services.config_service import list_admin_permissions, list_features, toggle_config
from bot.utils.permissions import require_owner

router = Router(name="owner_features")


@router.callback_query(lambda c: c.data and c.data.startswith("owner:features:toggle:"))
@require_owner
async def toggle_owner_features(callback: CallbackQuery, session: AsyncSession) -> None:
    """统一切换所有者功能开关

    功能说明:
    - 处理 `owner:features:toggle:*` 的所有功能开关，统一翻转配置并刷新功能面板

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
            "bot_all": ("bot.features.enabled", "机器人开关"),
            "user_all": ("user.features.enabled", "功能总开关"),
            "user_register": ("user.register", "Emby 注册"),
            "user_info": ("user.info", "账号信息"),
            "user_password": ("user.password", "修改密码"),
            "user_lines": ("user.lines", "线路信息"),
            "user_devices": ("user.devices", "设备管理"),
            "user_export_users": ("user.export_users", "导出用户功能"),
            "admin_open_registration": ("admin.open_registration", "管理员开放注册权限"),
        }
        if key not in mapping:
            await callback.answer("🔴 无效的开关项", show_alert=True)
            return
        config_key, label = mapping[key]
        new_val = await toggle_config(session, config_key)
        features = await list_features(session)
        if callback.message:
            await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
        await callback.answer(f"{'🟢' if new_val else '🔴'} {label}: {'启用' if new_val else '禁用'}")
    except Exception:
        await callback.answer("🔴 操作失败，请稍后重试", show_alert=True)


@router.callback_query(lambda c: c.data and c.data.startswith("owner:admin_perms:toggle:"))
@require_owner
async def toggle_admin_permissions(callback: CallbackQuery, session: AsyncSession) -> None:
    """统一切换管理员权限开关

    功能说明:
    - 处理 `owner:admin_perms:toggle:*` 的所有管理员权限开关，统一翻转配置并刷新权限面板

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
            "features": ("admin.features.enabled", "管理员功能总开关"),
            "groups": ("admin.groups", "群组管理权限"),
            "stats": ("admin.stats", "统计数据权限"),
            "hitokoto": ("admin.hitokoto", "一言管理权限"),
            "open_registration": ("admin.open_registration", "开放注册权限"),
        }
        if key not in mapping:
            await callback.answer("🔴 无效的权限项", show_alert=True)
            return
        config_key, label = mapping[key]
        new_val = await toggle_config(session, config_key)
        perms = await list_admin_permissions(session)
        if callback.message:
            await render_view(callback.message, get_common_image(), "🛡️ 管理员权限", get_admin_perms_panel_keyboard(perms))
        await callback.answer(f"{'🟢' if new_val else '🔴'} {label}: {'启用' if new_val else '禁用'}")
    except Exception:
        await callback.answer("🔴 操作失败，请稍后重试", show_alert=True)
