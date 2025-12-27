import re
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_USER_CHECKIN
from bot.keyboards.inline.constants import DAILY_CHECKIN_CALLBACK_DATA
from bot.services.currency import CurrencyService
from bot.utils.message import send_temp_message
from bot.utils.permissions import require_user_feature

router = Router(name="user_checkin")


@router.callback_query(F.data == DAILY_CHECKIN_CALLBACK_DATA)
@require_user_feature(KEY_USER_CHECKIN)
async def handle_daily_checkin(callback: CallbackQuery, session: AsyncSession):
    """处理每日签到回调

    功能说明:
    - 调用 CurrencyService 进行签到
    - 发送一条临时消息提示签到结果（10秒后自动删除）

    输入参数:
    - callback: CallbackQuery 对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    user_id = callback.from_user.id
    
    success, message = await CurrencyService.daily_checkin(session, user_id)
        
    # 发送签到结果消息并设置10秒后删除
    await send_temp_message(callback, message, 10)
        
    await callback.answer()
