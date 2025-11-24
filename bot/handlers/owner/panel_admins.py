from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.handlers.menu import render_view
from bot.keyboards.inline.panel_admins import AdminsPanelKeyboard
from bot.services.users import list_admins, remove_admin

router = Router(name="owner_admins")


@router.callback_query(F.data == "admins:list")
async def list_admins_view(callback: CallbackQuery, session, role: str) -> None:
    """查看管理员列表

    功能说明:
    - 显示当前标记为管理员的用户列表

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - role: 用户角色标识

    返回值:
    - None
    """
    if role != "owner":
        await callback.answer("❌ 此功能仅所有者可用", show_alert=True)
        return
    admins = await list_admins(session)
    lines = ["👮 管理员列表"]
    if not admins:
        lines.append("暂无管理员")
    else:
        for u in admins[:20]:
            label = f"ID:{u.id} 用户名:@{u.username or '无'}"
            lines.append(label)
    caption = "\n".join(lines)
    if callback.message:
        await render_view(callback.message, "assets/sakura.png", caption, AdminsPanelKeyboard.main())
    await callback.answer()

