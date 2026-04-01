
import html

from aiogram import Bot
from loguru import logger

from bot.core.config import settings
from bot.utils.text import build_user_link_html, escape_markdown_v2


def escape_markdown_v2_preserve_code(text: str) -> str:
    """
    功能说明:
    - 对输入文本按 MarkdownV2 规则进行转义, 但保留由反引号 ` 包裹的代码片段不转义
    - 用于避免像 `Unknown` 这样的片段被错误转义从而无法渲染成代码样式

    输入参数:
    - text: 原始文本

    返回值:
    - str: 处理后的文本, 代码片段保留, 其它内容按 MarkdownV2 转义
    """
    try:
        if not text:
            return ""
        parts = text.split("`")
        result: list[str] = []
        for idx, part in enumerate(parts):
            if idx % 2 == 0:
                # 代码片段之外: 做 MarkdownV2 转义
                result.append(escape_markdown_v2(part))
            else:
                # 代码片段之内: 保留原样, 并重新包裹反引号
                result.append(f"`{part}`")
        return "".join(result)
    except Exception:
        return escape_markdown_v2(text)


def _build_user_mention(full_name: str | None, user_id: str | None, _username: str | None) -> str:
    first_name = ""
    last_name = ""
    if full_name:
        parts = full_name.split(maxsplit=1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""
    return build_user_link_html(user_id, first_name, last_name)


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
        full_name = user_info.get("full_name", "Unknown")
        action = user_info.get("action", "UnknownAction")

        # 简单的 hashtag 处理：去除空格并转义
        def to_hashtag(s: str) -> str:
            clean_s = str(s).replace(" ", "").replace("#", "")
            return "#" + clean_s

        # 构造群组标识 Tag
        # 需求: 同时显示 @channelname (如果有) 和 #M100xxx (chat_id)
        # @lustfulboy #M1002216963051 #ID8134098953 #Leave
        group_tags_parts = []

        # 1. @channelname
        if chat_username:
             clean_chat_username = str(chat_username).lstrip("@").replace(" ", "")
             group_tags_parts.append("@" + clean_chat_username)

        # 2. #M100xxx (chat_id)
        if chat_id:
             # 将负号替换为 M，直接作为 ID 的一部分，前面加 #
             # 例如 -1002216963051 -> #M1002216963051
             chat_id_str = str(chat_id).replace("-", "M")
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
        user_mention = _build_user_mention(full_name, str(user_id), None)
        escaped_reason = html.escape(reason)

        content = f"📖 {user_mention} {escaped_reason}"
        msg_text = f"{tags}\n{content}"

        await bot.send_message(chat_id=settings.OWNER_MSG_GROUP, text=msg_text, parse_mode="HTML")
        logger.info(f"群组通知已发送至 {settings.OWNER_MSG_GROUP}")
    except Exception as e:
        logger.error(f"发送群组通知失败: {e}")
