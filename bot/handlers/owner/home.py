from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.inline.constants import OWNER_PANEL_LABEL
from bot.keyboards.inline.owner import get_owner_panel_keyboard
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_owner

router = Router(name="owner_home")


@router.callback_query(F.data == "owner:panel")
@require_owner
async def show_owner_panel(callback: CallbackQuery, main_msg: MainMessageService) -> None:
    """显示所有者主面板

    功能说明:
    - 展示所有者主面板与总开关状态

    输入参数:
    - callback: 回调对象
    - main_msg: 主消息服务

    返回值:
    - None
    """
    kb = get_owner_panel_keyboard()

    await main_msg.update_on_callback(callback, f"*{OWNER_PANEL_LABEL}*", kb)
    await callback.answer()

