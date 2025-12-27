from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.constants import ACCOUNT_CENTER_CALLBACK_DATA, BACK_TO_ACCOUNT_CALLBACK_DATA, ACCOUNT_CENTER_LABEL
from bot.keyboards.inline.user import get_account_center_keyboard
from bot.services.main_message import MainMessageService
from bot.services.users import has_emby_account
from bot.utils.permissions import require_user_feature

router = Router(name="user_account")


@router.callback_query(F.data.in_({ACCOUNT_CENTER_CALLBACK_DATA, BACK_TO_ACCOUNT_CALLBACK_DATA}))
@require_user_feature("user.account")
async def show_account_center(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """展示账号中心

    功能说明:
    - 展示二级账号中心菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    uid = callback.from_user.id if callback.from_user else None
    user_has_emby = False
    try:
        if uid:
            user_has_emby = await has_emby_account(session, uid)
    except Exception:
        user_has_emby = False

    kb = get_account_center_keyboard(user_has_emby)
    await main_msg.update_on_callback(callback, ACCOUNT_CENTER_LABEL, kb)
