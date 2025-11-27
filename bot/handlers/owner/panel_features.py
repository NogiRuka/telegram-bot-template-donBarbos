from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_owner import get_admin_perms_panel_keyboard, get_features_panel_keyboard
from bot.services.config_service import list_admin_permissions, list_features, toggle_config
from bot.utils.permissions import require_owner

router = Router(name="owner_features")


@router.callback_query(F.data == "owner:features:toggle:user_all")
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
    new_val = await toggle_config(session, "user.features.enabled")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 功能总开关: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:features:toggle:user_export_users")
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
    new_val = await toggle_config(session, "user.export_users")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 导出用户功能: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:features:toggle:user_register")
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
    new_val = await toggle_config(session, "user.register")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ Emby 注册: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:features:toggle:user_info")
@require_owner
async def toggle_user_info(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换用户功能: 账号信息"""
    new_val = await toggle_config(session, "user.info")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 账号信息: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:features:toggle:user_password")
@require_owner
async def toggle_user_password(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换用户功能: 修改密码"""
    new_val = await toggle_config(session, "user.password")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 修改密码: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:features:toggle:user_lines")
@require_owner
async def toggle_user_lines(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换用户功能: 线路信息"""
    new_val = await toggle_config(session, "user.lines")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 线路信息: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:features:toggle:user_devices")
@require_owner
async def toggle_user_devices(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换用户功能: 设备管理"""
    new_val = await toggle_config(session, "user.devices")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 设备管理: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:features:toggle:admin_open_registration")
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
    new_val = await toggle_config(session, "admin.open_registration")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 管理员开放注册权限: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:admin_perms:toggle:groups")
@require_owner
async def toggle_admin_perm_groups(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换管理员权限: 群组管理

    功能说明:
    - 切换管理员是否可使用群组管理功能

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "admin.permissions.groups")
    perms = await list_admin_permissions(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🛡️ 管理员权限", get_admin_perms_panel_keyboard(perms))
    await callback.answer(f"✅ 群组管理权限: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:admin_perms:toggle:stats")
@require_owner
async def toggle_admin_perm_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换管理员权限: 统计数据

    功能说明:
    - 切换管理员是否可使用统计数据功能

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "admin.permissions.stats")
    perms = await list_admin_permissions(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🛡️ 管理员权限", get_admin_perms_panel_keyboard(perms))
    await callback.answer(f"✅ 统计数据权限: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:admin_perms:toggle:open_registration")
@require_owner
async def toggle_admin_perm_open_registration(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换管理员权限: 开放注册

    功能说明:
    - 切换管理员是否可使用开放注册功能

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "admin.permissions.open_registration")
    perms = await list_admin_permissions(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🛡️ 管理员权限", get_admin_perms_panel_keyboard(perms))
    await callback.answer(f"✅ 开放注册权限: {'启用' if new_val else '禁用'}")


@router.callback_query(F.data == "owner:admin_perms:toggle:features")
@require_owner
async def toggle_admin_features_enabled(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换管理员功能总开关

    功能说明:
    - 切换 `admin.features.enabled` 并刷新管理员权限面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "admin.features.enabled")
    perms = await list_admin_permissions(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🛡️ 管理员权限", get_admin_perms_panel_keyboard(perms))
    await callback.answer(f"✅ 管理员功能总开关: {'启用' if new_val else '禁用'}")

@router.callback_query(F.data == "owner:features:toggle:bot_all")
@require_owner
async def toggle_bot_features(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换机器人功能总开关

    功能说明:
    - 切换 `bot.features.enabled` 状态并刷新功能面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "bot.features.enabled")
    features = await list_features(session)
    if callback.message:
        await render_view(callback.message, get_common_image(), "🧩 功能开关", get_features_panel_keyboard(features))
    await callback.answer(f"✅ 机器人开关: {'启用' if new_val else '禁用'}")
