from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.constants import DAILY_CHECKIN_CALLBACK_DATA
from bot.services.currency import CurrencyService

router = Router(name="user_checkin")


from bot.handlers.start import build_home_view
from bot.services.main_message import MainMessageService
from bot.utils.images import get_common_image

@router.callback_query(F.data == DAILY_CHECKIN_CALLBACK_DATA)
async def handle_daily_checkin(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """处理每日签到回调

    功能说明:
    - 调用 CurrencyService 进行签到
    - 将签到结果显示在主文案下方

    输入参数:
    - callback: CallbackQuery 对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    user_id = callback.from_user.id
    
    success, message = await CurrencyService.daily_checkin(session, user_id)
        
    # 获取首页内容并追加签到消息
    caption, kb = await build_home_view(session, user_id, append_text=message)
    
    await main_msg.update_on_callback(callback, caption, kb, get_common_image())
    await callback.answer()
