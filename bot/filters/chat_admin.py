from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import BaseFilter
from aiogram.types import Message


class GroupAdminFilter(BaseFilter):
    """
    Check if the user is an admin or creator of the group chat.
    Returns False for private chats.
    """

    async def __call__(self, message: Message) -> bool:
        if message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            return False

        if not message.from_user:
            return False

        try:
            member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
            return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
        except Exception:
            return False
