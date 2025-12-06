from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.images import get_common_image
from bot.keyboards.inline.start_owner import get_features_panel_keyboard
from bot.services.config_service import list_features, toggle_config
from bot.utils.permissions import require_owner
from bot.utils.view import render_view

router = Router(name="owner_features")


@router.callback_query(F.data == "owner:features")
@require_owner
async def show_features_panel(callback: CallbackQuery, session: AsyncSession) -> None:
    """显示功能开关面板

    功能说明:
    - 跳转到功能开关子面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    caption = "🧩 功能开关\n\n可切换全部功能或单项功能"
    features = await list_features(session)
    kb = get_features_panel_keyboard(features)
    msg = callback.message
    if isinstance(msg, types.Message):
        image = get_common_image()
        await render_view(msg, image, caption, kb)
    await callback.answer()


@router.callback_query(F.data == "owner:toggle:bot")
@require_owner
async def toggle_bot_enabled(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换机器人总开关

    功能说明:
    - 翻转 `bot.features.enabled` 状态并返回提示

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "bot.features.enabled")
    await callback.answer(f"{'🟢' if new_val else '🔴'} 机器人总开关: {'开启' if new_val else '关闭'}")


@router.callback_query(lambda c: c.data and c.data.startswith("owner:features:toggle:"))
@require_owner
async def toggle_owner_features(callback: CallbackQuery, session: AsyncSession) -> None:
    """统一切换所有者功能开关

    功能说明:
    - 处理 `owner:features:toggle:*` 的所有功能开关, 统一翻转配置并刷新功能面板

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
        operator_id = callback.from_user.id if getattr(callback, "from_user", None) else None
        new_val = await toggle_config(session, config_key, operator_id=operator_id)
        features = await list_features(session)
        msg = callback.message
        if isinstance(msg, types.Message):
            await render_view(msg, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
        await callback.answer(f"{'🟢' if new_val else '🔴'} {label}: {'启用' if new_val else '禁用'}")
    except Exception:
        await callback.answer("🔴 操作失败，请稍后重试", show_alert=True)

