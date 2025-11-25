from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.handlers.menu import render_view
from bot.keyboards.inline.panel_features import FeaturesPanelKeyboard
from bot.services.config_service import toggle_config

router = Router(name="owner_features")


@router.callback_query(F.data == "features:toggle:all")
async def toggle_all_features(callback: CallbackQuery, session, role: str) -> None:
    """切换全部功能开关

    功能说明:
    - 翻转 `features_enabled` 状态

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - role: 用户角色标识

    返回值:
    - None
    """
    if role != "owner":
        await callback.answer("❌ 此操作仅所有者可用", show_alert=True)
        return
    new_val = await toggle_config(session, "features_enabled")
    await callback.answer(f"✅ 功能总开关: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "features:toggle:export_users")
async def toggle_export_users(callback: CallbackQuery, session, role: str) -> None:
    """切换导出用户功能

    功能说明:
    - 翻转 `feature_export_users` 状态

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - role: 用户角色标识

    返回值:
    - None
    """
    if role != "owner":
        await callback.answer("❌ 此操作仅所有者可用", show_alert=True)
        return
    new_val = await toggle_config(session, "feature_export_users")
    await callback.answer(f"✅ 导出用户功能: {'启用' if new_val else '禁用'}")

