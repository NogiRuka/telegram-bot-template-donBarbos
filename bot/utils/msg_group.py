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
        # Reason 已经是 MarkdownV2 格式（如果包含列表），或者纯文本
        # 这里假设 reason 传入时已经是处理过的（例如包含列表），或者纯文本需要转义
        # 但考虑到外部传入的 reason 可能包含 \n 和 * 等标记，这里应该谨慎处理
        # 如果 reason 来自 admin_service，它已经包含了格式化内容（如列表符号）
        # 最安全的做法是：让调用方保证 reason 的格式安全，或者在这里统一转义
        # 鉴于之前我们在 admin_service 里构造了带有列表符号的文本，这里不应该再次全量转义 reason
        # 但 full_name 需要转义
        
        # 修正：admin_service 里的 reason 只是普通文本拼接，没有进行 markdown 转义
        # 所以这里我们需要对 full_name 进行转义，reason 如果包含我们自己加的格式，那部分应该是安全的，
        # 但 reason 中的动态内容（如错误信息）需要转义。
        # 这是一个两难：如果 reason 是 "Reason\n• Item"，转义后变成 "Reason\n\\• Item"，列表符号失效。
        # 更好的做法是：admin_service 传递 reason 时，已经做好了转义工作。
        # 检查 admin_service.py:
        # reason = f"{reason}\n\n📝 *处理结果*:\n{results_str}"
        # 这里的 reason 包含了 *，所以它是 Markdown 格式的。
        # 但是 results_str 里的内容（错误信息）没有被转义。
        # 所以我们需要在 admin_service 里就做好转义，或者在这里假设 reason 是 MarkdownV2 Ready 的。
        # 既然用户要求 msg_group.py 改为 MarkdownV2，那我们就改这里。
        # 为了兼容性，我们假设 reason 中的动态部分已经在上游转义了（或者我们在这里只转义 full_name）
        # 实际上，admin_service 里构造的 reason 包含未转义的 reason 原始文本和 results。
        # 让我们先在 msg_group.py 里只转义 full_name，并假设 reason 是安全的 MarkdownV2 字符串。
        # 但如果 reason 是纯文本（如 "封禁原因"），直接发 MarkdownV2 会报错吗？
        # 如果 reason 不含特殊字符没事，含了就报错。
        # 稳妥起见，我们应该在这个函数里对 reason 进行 escape_markdown_v2，除非它已经是 MarkdownV2。
        # 但我们无法区分。
        # 妥协方案：将 reason 当作 MarkdownV2 处理。
        # 在 admin_service.py 里，我们需要确保传入的 reason 是转义过的。
        # 现在先改 msg_group.py，使用 code block 包裹 full_name
        
        escaped_full_name = escape_markdown_v2(full_name)
        # content = f"📖 `{escaped_full_name}` {reason}"
        # 注意：reason 如果包含 * 等，必须是有效的 MarkdownV2。
        # 如果上游传的是纯文本，这里直接拼接入 MarkdownV2 会有问题。
        # 我们先按用户要求改为 MarkdownV2，并转义 full_name。
        # 至于 reason，我们在 admin_service.py 里处理转义。
        
        content = f"📖 `{escaped_full_name}` {reason}"
        msg_text = f"{tags}\n{content}"

        await bot.send_message(chat_id=settings.OWNER_MSG_GROUP, text=msg_text, parse_mode="MarkdownV2")
        logger.info(f"群组通知已发送至 {settings.OWNER_MSG_GROUP}")
    except Exception as e:
        logger.error(f"发送群组通知失败: {e}")
