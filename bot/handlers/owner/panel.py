from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_owner import (
    get_admin_perms_panel_keyboard,
    get_admins_panel_keyboard,
    get_features_panel_keyboard,
    get_owner_panel_keyboard,
)
from bot.services.config_service import list_admin_permissions, list_features, toggle_config
from bot.utils.permissions import require_owner

router = Router(name="owner_panel")


@router.callback_query(F.data == "owner:panel")
@require_owner
async def show_owner_panel(callback: CallbackQuery) -> None:
    """显示所有者主面板

    功能说明:
    - 展示所有者主面板与总开关状态

    输入参数:
    - callback: 回调对象

    返回值:
    - None
    """
    caption = "🛠️ 管理面板\n\n可进行机器人总开关、功能开关与管理员管理"
    kb = get_owner_panel_keyboard()
    if callback.message:
        image = get_common_image()
        ok = await render_view(callback.message, image, caption, kb)
        if not ok:
            await callback.answer("界面未更新, 请重试", show_alert=True)
            return
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
    await callback.answer(f"✅ 机器人总开关: {'开启' if new_val else '关闭'}")


@router.callback_query(F.data == "owner:features")
@require_owner
async def show_features_panel(callback: CallbackQuery, session: AsyncSession) -> None:
    """显示功能开关面板

    功能说明:
    - 跳转到功能开关子面板

    输入参数:
    - callback: 回调对象

    返回值:
    - None
    """

    caption = "🧩 功能开关\n\n可切换全部功能或单项功能"
    # 读取当前功能开关状态并渲染状态键盘
    features = await list_features(session)
    kb = get_features_panel_keyboard(features)
    if callback.message:
        image = get_common_image()
        await render_view(callback.message, image, caption, kb)
    await callback.answer()


@router.callback_query(F.data == "owner:admins")
@require_owner
async def show_admins_panel(callback: CallbackQuery) -> None:
    """显示管理员管理面板

    功能说明:
    - 跳转到管理员管理子面板

    输入参数:
    - callback: 回调对象

    返回值:
    - None
    """

    caption = "👮 管理员管理\n\n可查看管理员列表与管理权限"
    kb = get_admins_panel_keyboard()
    if callback.message:
        image = get_common_image()
        await render_view(callback.message, image, caption, kb)
    await callback.answer()


# 所有“返回主面板”统一通过 home:back 由通用处理器处理
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
    if callback.message:
        image = get_common_image()
        await render_view(callback.message, image, "🛡️ 管理员权限", kb)
    await callback.answer()
