from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_owner import get_admins_panel_keyboard
from bot.services.users import list_admins
from bot.utils.permissions import _resolve_role, require_owner
from bot.utils.view import render_view

router = Router(name="owner_admins")


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
    msg = callback.message
    if isinstance(msg, types.Message):
        image = get_common_image()
        await render_view(msg, image, caption, kb)
    await callback.answer()


@router.callback_query(F.data == "owner:admins:list")
@require_owner
async def list_admins_view(callback: CallbackQuery, session: AsyncSession) -> None:
    """查看管理员列表

    功能说明:
    - 显示当前标记为管理员的用户列表

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    admins = await list_admins(session)
    lines = ["👮 管理员列表"]
    filtered: list[int] = []
    for u in admins:
        role = await _resolve_role(session, u.id)
        if role != "owner":
            filtered.append(u.id)
    if not filtered:
        lines.append("暂无管理员")
    else:
        for u in admins[:20]:
            role = await _resolve_role(session, u.id)
            if role == "owner":
                continue
            label = f"ID:{u.id} 用户名:@{u.username or '无'}"
            lines.append(label)
    caption = "\n".join(lines)
    msg = callback.message
    if isinstance(msg, types.Message):
        image = get_common_image()
        await render_view(msg, image, caption, get_admins_panel_keyboard())
    await callback.answer()

