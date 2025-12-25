import re
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.constants import DAILY_CHECKIN_CALLBACK_DATA
from bot.services.currency import CurrencyService
from bot.handlers.start import build_home_view
from bot.services.main_message import MainMessageService
from bot.utils.images import get_common_image
from bot.utils.message import delete_message_after_delay

router = Router(name="user_checkin")


@router.callback_query(F.data == DAILY_CHECKIN_CALLBACK_DATA)
async def handle_daily_checkin(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """处理每日签到回调

    功能说明:
    - 调用 CurrencyService 进行签到
    - 刷新主面板（保持一言内容）
    - 发送一条临时消息提示签到结果（10秒后自动删除）

    输入参数:
    - callback: CallbackQuery 对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    user_id = callback.from_user.id
    
    success, message = await CurrencyService.daily_checkin(session, user_id)
        
    # 尝试从当前 caption 中提取一言内容，避免刷新
    hitokoto_payload = None
    current_caption = callback.message.caption or callback.message.text
    if current_caption:
        # 匹配 『 内容 』 格式
        match = re.search(r"^『\s*(.*?)\s*』", current_caption)
        if match:
            hitokoto_payload = {"hitokoto": match.group(1)}

    # 获取首页内容（不追加签到消息）
    caption, kb = await build_home_view(
        session, 
        user_id, 
        hitokoto_payload=hitokoto_payload
    )
    
    await main_msg.update_on_callback(callback, caption, kb, get_common_image())
    
    # 发送签到结果消息并设置10秒后删除
    if callback.message:
        sent_msg = await callback.message.answer(text=message)
        delete_message_after_delay(sent_msg, 10)
        
    await callback.answer()
