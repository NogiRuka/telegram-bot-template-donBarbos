from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.start_user import get_account_center_keyboard
from bot.services.users import has_emby_account
from bot.utils.images import get_common_image
from bot.utils.permissions import _resolve_role
from bot.utils.view import render_view

router = Router(name="user_account_center")


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
    uid = callback.from_user.id if callback.from_user else None
    has_emby = False
    try:
        if uid:
            has_emby = await has_emby_account(session, uid)
    except Exception:
        has_emby = False

    kb = get_account_center_keyboard(has_emby)
    msg = callback.message
    if isinstance(msg, types.Message):
        await _resolve_role(session, uid)
        image = get_common_image()
        await render_view(msg, image, "🧩 账号中心", kb)
    await callback.answer()

