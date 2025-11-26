from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.keyboards.inline.panel_admins import AdminsPanelKeyboard
from bot.keyboards.inline.panel_features import FeaturesPanelKeyboard
from bot.keyboards.inline.panel_main import OwnerPanelKeyboard
from bot.keyboards.inline.start_owner import get_start_owner_keyboard
from bot.services.config_service import toggle_config
from bot.utils.permissions import require_owner

router = Router(name="owner_panel")


@router.callback_query(F.data == "panel:main")
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
    kb = OwnerPanelKeyboard.main()
    if callback.message:
        await render_view(callback.message, "assets/ui/panel_general.jpg", caption, kb)
    await callback.answer()


@router.callback_query(F.data == "panel:toggle:bot")
@require_owner
async def toggle_bot_enabled(callback: CallbackQuery, session: AsyncSession) -> None:
    """切换机器人总开关

    功能说明:
    - 翻转 `bot_enabled` 状态并返回提示

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    new_val = await toggle_config(session, "bot_enabled")
    await callback.answer(f"✅ 机器人总开关: {'开启' if new_val else '关闭'}")


@router.callback_query(F.data == "panel:features")
@require_owner
async def show_features_panel(callback: CallbackQuery) -> None:
    """显示功能开关面板

    功能说明:
    - 跳转到功能开关子面板

    输入参数:
    - callback: 回调对象

    返回值:
    - None
    """

    caption = "🧩 功能开关\n\n可切换全部功能或单项功能"
    kb = FeaturesPanelKeyboard.main()
    if callback.message:
        await render_view(callback.message, "assets/ui/panel_general.jpg", caption, kb)
    await callback.answer()


@router.callback_query(F.data == "panel:admins")
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
    kb = AdminsPanelKeyboard.main()
    if callback.message:
        await render_view(callback.message, "assets/ui/panel_general.jpg", caption, kb)
    await callback.answer()


@router.callback_query(F.data == "panel:back")
@require_owner
async def back_to_start(callback: CallbackQuery) -> None:
    """返回首页

    功能说明:
    - 返回到所有者首页

    输入参数:
    - callback: 回调对象

    返回值:
    - None
    """
    if callback.message:
        await render_view(callback.message, "assets/ui/start_owner.jpg", "返回首页", get_start_owner_keyboard())
    await callback.answer()
