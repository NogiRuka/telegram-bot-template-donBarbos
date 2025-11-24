from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import Message
from loguru import logger
from bot.core.config import settings

from bot.services.users import add_user, user_exists

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject
    from sqlalchemy.ext.asyncio import AsyncSession


class AuthMiddleware(BaseMiddleware):
    def _get_role(self, user_id: int) -> str:
        """判定用户角色

        功能说明:
        - 基于配置的 `OWNER_ID` 与 `ADMIN_IDS` 判定用户角色

        输入参数:
        - user_id: Telegram 用户ID

        返回值:
        - str: 角色标识，取值为 "owner" | "admin" | "user"
        """
        try:
            owner_id = settings.get_owner_id()
            if user_id == owner_id:
                return "owner"
        except Exception:
            pass

        if user_id in set(settings.get_admin_ids()):
            return "admin"
        return "user"
        
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

        if not user:
            return await handler(event, data)

        # 注入角色到上下文
        data["role"] = self._get_role(user.id)

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
