import logging
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import BaseFilter
from aiogram.types import Message

logger = logging.getLogger(__name__)

class GroupAdminFilter(BaseFilter):
    """
    Check if the user is an admin or creator of the group chat.
    Returns False for private chats.
    """

    async def __call__(self, message: Message, **kwargs) -> bool:
        logger.info(f"GroupAdminFilter checking for chat type: {message.chat.type}, user: {message.from_user.id if message.from_user else 'None'}")
        
        # 如果是私聊，允许通过过滤器（后续逻辑会检查参数）
        if message.chat.type == ChatType.PRIVATE:
            logger.info("GroupAdminFilter allowed for private chat")
            return True

        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return False

        if not message.from_user:
            return False

        try:
            member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            is_admin = member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
            logger.info(f"GroupAdminFilter result for user {message.from_user.id} in chat {message.chat.id}: {is_admin}")
            return is_admin
        except Exception as e:
            logger.error(f"GroupAdminFilter error: {e}")
            return False
