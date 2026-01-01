import html

from aiogram import Bot
from loguru import logger

from bot.core.config import settings


async def send_group_notification(
    bot: Bot,
    user_info: dict[str, str],
    reason: str,
) -> None:
    """
    发送群组通知（通用版）
    
    格式:
    #GroupTitle #IDUserID #Username #Action
    📖 FullName Reason
    """
    logger.info(f"尝试发送群组通知: group={settings.OWNER_MSG_GROUP}")
    
    if not bot or not settings.OWNER_MSG_GROUP or not user_info:
        return

    try:
        group_name = user_info.get("group_name", "UnknownGroup")
        user_id = user_info.get("user_id", "UnknownID")
        username = user_info.get("username", "UnknownUser")
        full_name = user_info.get("full_name", "Unknown")
        action = user_info.get("action", "UnknownAction")

        # 简单的 hashtag 处理：去除空格
        def to_hashtag(s: str) -> str:
            return "#" + str(s).replace(" ", "").replace("#", "")

        # #GroupTitle #IDUserID #Username #Action
        tags = f"{to_hashtag(group_name)} #ID{user_id} {to_hashtag(username)} {to_hashtag(action)}"
        
        # 📖 FullName Reason
        content = f"📖 {html.escape(full_name)} {html.escape(reason)}"
        
        msg_text = f"{tags}\n{content}"

        await bot.send_message(chat_id=settings.OWNER_MSG_GROUP, text=msg_text, parse_mode="HTML")
        logger.info(f"群组通知已发送至 {settings.OWNER_MSG_GROUP}")
    except Exception as e:
        logger.error(f"发送群组通知失败: {e}")
