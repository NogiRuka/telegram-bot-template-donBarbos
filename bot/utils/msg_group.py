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
        # 优先使用 chat_username (即 @channelname)，如果没有则使用 chat_id，不再使用 group_name (Title)
        # 注意: user_info 中需要传入 chat_username 或 chat_id
        chat_identifier = user_info.get("chat_username")
        if not chat_identifier:
            chat_id = user_info.get("chat_id")
            if chat_id:
                # 确保是字符串，并处理可能的负号
                chat_identifier = f"ID{str(chat_id).replace('-', 'M')}" # 替换负号避免 hashtag 问题，或者直接拼接
            else:
                # 如果都没有，回退到 group_name 但尽量不使用
                chat_identifier = user_info.get("group_name", "UnknownGroup")

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
        # 如果是 @channelname 格式，直接作为 Tag 或者 Mention
        # 用户希望: 数字ID用#，或者@channelname的形式
        group_tag = ""
        if str(chat_identifier).startswith("@"):
             # 如果已经包含 @，则当作 mention 处理 (去除 @ 后再加 @)
             group_tag = to_mention(str(chat_identifier).lstrip("@"))
        else:
             # 否则作为 hashtag
             group_tag = to_hashtag(chat_identifier)

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
