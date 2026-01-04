from functools import wraps

from aiogram.enums import ChatType
from aiogram.types import Message


def private_chat_only(func):
    """
    装饰器：仅允许在私聊中使用命令
    如果要启用群组支持，只需注释掉此装饰器即可
    """
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if message.chat.type != ChatType.PRIVATE:
            return None
        return await func(message, *args, **kwargs)
    return wrapper
