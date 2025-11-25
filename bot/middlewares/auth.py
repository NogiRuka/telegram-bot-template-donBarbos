from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.database.models import UserExtendModel, UserRole
from bot.services.users import upsert_user_on_interaction

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject
    from sqlalchemy.ext.asyncio import AsyncSession


class AuthMiddleware(BaseMiddleware):

    async def _get_role_from_db(self, session: AsyncSession, user_id: int) -> str:
        """判定用户角色

        功能说明:
        - 从数据库 `user_extend` 读取角色

        输入参数:
        - session: 异步数据库会话
        - user_id: Telegram 用户ID

        返回值:
        - str: 角色标识, 取值为 "owner" | "admin" | "user"
        """
        result = await session.execute(
            select(UserExtendModel.role).where(UserExtendModel.user_id == user_id)
        )
        role = result.scalar_one_or_none()
        if role == UserRole.owner:
            return "owner"
        if role == UserRole.admin:
            return "admin"
        return "user"

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        session: AsyncSession = data["session"]

        # 支持 Message 与 CallbackQuery 两类事件
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        else:
            return await handler(event, data)

        if not user:
            return await handler(event, data)

        # 交互时对用户进行更新/新增与快照(同步角色配置到库)
        await upsert_user_on_interaction(session=session, user=user)

        # 注入角色到上下文(从数据库读取)
        data["role"] = await self._get_role_from_db(session, user.id)

        return await handler(event, data)
