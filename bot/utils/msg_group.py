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
        # 需求: 同时显示 @channelname (如果有) 和 #M100xxx (chat_id)
        # @lustfulboy #M1002216963051 #ID8134098953 #Leave
        group_tags_parts = []
        
        # 1. @channelname
        if chat_username:
             group_tags_parts.append(to_mention(str(chat_username).lstrip("@")))
        
        # 2. #M100xxx (chat_id)
        if chat_id:
             # 将负号替换为 M，直接作为 ID 的一部分，前面加 #
             # 例如 -1002216963051 -> #M1002216963051
             chat_id_str = str(chat_id).replace('-', 'M')
             group_tags_parts.append(to_hashtag(chat_id_str))
        
        # 如果两者都没有，回退到 group_name
        if not group_tags_parts:
             group_name = user_info.get("group_name", "UnknownGroup")
             group_tags_parts.append(to_hashtag(group_name))

        group_tag_str = " ".join(group_tags_parts)

        # Tag 格式: GroupTag(s) #IDUserID #Action
        # 注意：这里不再包含 @Username，因为它移到了正文中
        tags = f"{group_tag_str} {to_hashtag('ID' + str(user_id))} {to_hashtag(action)}"
        
        # 📖 FullName @Username Reason
        escaped_full_name = escape_markdown_v2(full_name)
        user_mention = to_mention(username)
        
        content = f"📖 `{escaped_full_name}` {user_mention} {reason}"
        msg_text = f"{tags}\n{content}"

        await bot.send_message(chat_id=settings.OWNER_MSG_GROUP, text=msg_text, parse_mode="MarkdownV2")
        logger.info(f"群组通知已发送至 {settings.OWNER_MSG_GROUP}")
    except Exception as e:
        logger.error(f"发送群组通知失败: {e}")
