from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.config_service import toggle_config
from bot.utils.permissions import require_owner

router = Router(name="owner_features")


@router.callback_query(F.data == "features:toggle:all")
@require_owner
async def toggle_all_features(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换全部功能开关

    功能说明:
    - 翻转 `features_enabled` 状态

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "features_enabled")
    await callback.answer(f"✅ 功能总开关: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "features:toggle:export_users")
@require_owner
async def toggle_export_users(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换导出用户功能

    功能说明:
    - 翻转 `feature_export_users` 状态

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "feature_export_users")
    await callback.answer(f"✅ 导出用户功能: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "features:toggle:emby_register")
@require_owner
async def toggle_emby_register(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换 Emby 注册功能

    功能说明:
    - 翻转 `feature_emby_register` 状态

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "feature_emby_register")
    await callback.answer(f"✅ Emby 注册: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "features:toggle:admin_open_registration")
@require_owner
async def toggle_admin_open_registration(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换管理员开放注册权限

    功能说明:
    - 翻转 `feature_admin_open_registration` 状态

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "feature_admin_open_registration")
    await callback.answer(f"✅ 管理员开放注册权限: {'启用' if new_val else '禁用'}")
