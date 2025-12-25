from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.constants import DAILY_CHECKIN_CALLBACK_DATA
from bot.services.currency import CurrencyService

router = Router(name="user_checkin")


@router.callback_query(F.data == DAILY_CHECKIN_CALLBACK_DATA)
async def handle_daily_checkin(callback: CallbackQuery, session: AsyncSession):
    """处理每日签到回调

    功能说明:
    - 调用 CurrencyService 进行签到
    - 弹窗提示签到结果

    输入参数:
    - callback: CallbackQuery 对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    user_id = callback.from_user.id
    
    success, message = await CurrencyService.daily_checkin(session, user_id)
        
    await callback.answer(text=message, show_alert=True)
