from aiogram import F, Router, types
from aiogram.types import CallbackQuery

from bot.keyboards.inline.start_owner import get_owner_panel_keyboard
from bot.utils.images import get_common_image
from bot.utils.permissions import require_owner
from bot.utils.view import render_view

router = Router(name="owner_home")


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
    caption = "👑 所有者面板"
    kb = get_owner_panel_keyboard()
    msg = callback.message
    if isinstance(msg, types.Message):
        image = get_common_image()
        ok = await render_view(msg, image, caption, kb)
        if not ok:
            await callback.answer("界面未更新, 请重试", show_alert=True)
            return
    await callback.answer()

