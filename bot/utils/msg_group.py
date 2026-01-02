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
    logger.info(f"尝试发送群组通知: group={settings.OWNER_MSG_GROUP}, user_info={user_info}")
    if not bot or not settings.OWNER_MSG_GROUP or not user_info:
        return

    try:
        chat_username = user_info.get("chat_username")
        chat_id = user_info.get("chat_id")
        
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

        # 处理 username 为提及 (@username)
        def to_mention(s: str) -> str:
            clean_s = str(s).replace(" ", "").replace("@", "")
            return "@" + escape_markdown_v2(clean_s)

        # 构造群组标识 Tag
        # 优先使用 chat_username (即 @channelname)，如果没有则使用 chat_id
        group_tag = ""
        if chat_username:
             # 有 username，强制作为 mention (Telegram API 返回的 username 通常不带 @)
             group_tag = to_mention(str(chat_username).lstrip("@"))
        elif chat_id:
             # 没有 username，使用 ID 生成 hashtag
             # 确保是字符串，并处理可能的负号 (替换为 M 避免 hashtag 问题)
             chat_identifier = f"ID{str(chat_id).replace('-', 'M')}" 
             group_tag = to_hashtag(chat_identifier)
        else:
             # 如果都没有，回退到 group_name 但尽量不使用
             group_name = user_info.get("group_name", "UnknownGroup")
             group_tag = to_hashtag(group_name)

        # Tag 格式: GroupTag #IDUserID @Username #Action
        tags = f"{group_tag} {to_hashtag('ID' + str(user_id))} {to_mention(username)} {to_hashtag(action)}"
        
        # 📖 FullName Reason
        escaped_full_name = escape_markdown_v2(full_name)
        
        content = f"📖 `{escaped_full_name}` {reason}"
        msg_text = f"{tags}\n{content}"

        await bot.send_message(chat_id=settings.OWNER_MSG_GROUP, text=msg_text, parse_mode="MarkdownV2")
        logger.info(f"群组通知已发送至 {settings.OWNER_MSG_GROUP}")
    except Exception as e:
        logger.error(f"发送群组通知失败: {e}")
