
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_user import get_account_center_keyboard
from bot.services.config_service import get_config
from bot.utils.permissions import _resolve_role

router = Router(name="user_account")


@router.callback_query(F.data == "user:account")
async def show_account_center(callback: CallbackQuery, session: AsyncSession) -> None:
    """展示账号中心

    功能说明:
    - 展示二级账号中心菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    has_emby_account = True
    kb = get_account_center_keyboard(has_emby_account)
    msg = callback.message
    if msg:
        uid = callback.from_user.id if callback.from_user else None
        await _resolve_role(session, uid)
        image = get_common_image()
        await render_view(msg, image, "🧾 账号中心", kb)
    await callback.answer()


@router.callback_query(
    F.data.in_(
        {
            "user:register",
            "user:info",
            "user:lines",
            "user:devices",
            "user:password",
            "user:profile",
        }
    )
)
async def placeholder_callbacks(callback: CallbackQuery, session: AsyncSession) -> None:
    """占位回调处理器

    功能说明:
    - 处理尚未实现的功能入口, 避免点击按钮无响应

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    data = callback.data or ""
    feature_map: dict[str, str] = {
        "user:register": "user.register",
        "user:info": "user.info",
        "user:lines": "user.lines",
        "user:devices": "user.devices",
        "user:password": "user.password",
    }
    key = feature_map.get(data)
    if key:
        enabled_all = bool(await get_config(session, "user.features.enabled") or False)
        enabled_feature = bool(await get_config(session, key) or False)
        if not (enabled_all and enabled_feature):
            await callback.answer("❌ 该功能当前不可用", show_alert=True)
            return
    await callback.answer("功能建设中, 请稍后再试", show_alert=True)
