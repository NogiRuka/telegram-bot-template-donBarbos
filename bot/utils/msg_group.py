import html

from aiogram import Bot
from loguru import logger

from bot.core.config import settings
from bot.utils.text import escape_markdown_v2


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

        # 简单的 hashtag 处理：去除空格并转义
        def to_hashtag(s: str) -> str:
            # 先去除不合法字符，再转义 MarkdownV2 字符
            # 注意: hashtag 内部不能有空格，但 MarkdownV2 要求转义 #
            clean_s = str(s).replace(" ", "").replace("#", "")
            return "\\#" + escape_markdown_v2(clean_s)

        # #GroupTitle #IDUserID #Username #Action
        tags = f"{to_hashtag(group_name)} {to_hashtag('ID' + str(user_id))} {to_hashtag(username)} {to_hashtag(action)}"
        
        # 📖 FullName Reason
        escaped_full_name = escape_markdown_v2(full_name)
        
        content = f"📖 `{escaped_full_name}` {reason}"
        msg_text = f"{tags}\n{content}"

        await bot.send_message(chat_id=settings.OWNER_MSG_GROUP, text=msg_text, parse_mode="MarkdownV2")
        logger.info(f"群组通知已发送至 {settings.OWNER_MSG_GROUP}")
    except Exception as e:
        logger.error(f"发送群组通知失败: {e}")
