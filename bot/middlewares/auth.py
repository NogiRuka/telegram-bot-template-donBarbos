from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import Message
from loguru import logger

from bot.services.users import add_user, user_exists

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject
    from sqlalchemy.ext.asyncio import AsyncSession


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        session: AsyncSession = data["session"]
        message: Message = event
        user = message.from_user

        # 打印 message 对象结构，方便调试
        logger.debug(f"message 结构: {message}")

        if not user:
            return await handler(event, data)

        if await user_exists(session, user.id):
            return await handler(event, data)

        # 记录新用户信息：user_id、用户名、全名
        logger.info(
            f"新用户注册 | user_id: {user.id} | "
            f"用户名: @{user.username or '无'} | "
            f"全名: {user.full_name}"
        )

        await add_user(session=session, user=user)

        return await handler(event, data)
