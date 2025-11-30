from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.permissions import require_admin_feature, require_admin_priv

router = Router(name="admin_groups")


@router.callback_query(F.data == "admin:groups")
@require_admin_priv
@require_admin_feature("admin.groups")
async def open_groups_feature(callback: CallbackQuery, _session: AsyncSession) -> None:
    """打开群组管理功能

    功能说明:
    - 管理员面板中的群组管理入口占位处理, 功能关闭时提示不可用

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await callback.answer("功能建设中, 请使用 /admin_groups 命令", show_alert=True)

