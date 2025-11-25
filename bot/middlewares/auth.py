from __future__ import annotations
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from bot.core.config import settings
from bot.services.users import upsert_user_on_interaction

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import TelegramObject
    from sqlalchemy.ext.asyncio import AsyncSession


class AuthMiddleware(BaseMiddleware):
    _bot_id: int | None = None
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
        session: AsyncSession = data["session"]

        # 支持 Message 与 CallbackQuery 两类事件
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        else:
            return await handler(event, data)

        if not user:
            return await handler(event, data)

        # 注入角色到上下文
        data["role"] = self._get_role(user.id)

        # 交互时对用户进行更新/新增与快照
        await upsert_user_on_interaction(session=session, user=user)

        return await handler(event, data)
