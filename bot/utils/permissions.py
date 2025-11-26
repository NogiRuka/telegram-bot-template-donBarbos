from __future__ import annotations
import contextlib
import functools
from typing import TYPE_CHECKING, Any

from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.core.config import settings
from bot.database.models import UserExtendModel, UserRole

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncSession


def require_owner(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """所有者权限装饰器

    功能说明:
    - 在调用处理器前检查 `role` 是否为 "owner", 否则提示无权限

    输入参数:
    - func: 需要保护的异步处理器函数

    返回值:
    - Callable[..., Awaitable[Any]]: 包装后的处理器函数
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        role: str | None = kwargs.get("role")
        if role is None:
            session: AsyncSession | None = kwargs.get("session")
            user_id: int | None = None
            first = args[0] if args else None
            if (isinstance(first, CallbackQuery) and first.from_user) or (isinstance(first, Message) and first.from_user):
                user_id = first.from_user.id
            if session and user_id is not None:
                result = await session.execute(
                    select(UserExtendModel.role).where(UserExtendModel.user_id == user_id)
                )
                r = result.scalar_one_or_none()
                if r == UserRole.owner:
                    role = "owner"
                elif r == UserRole.admin:
                    role = "admin"
                else:
                    role = "user"
            else:
                with contextlib.suppress(Exception):
                    if user_id is not None and user_id == settings.get_owner_id():
                        role = "owner"
                    elif user_id is not None and user_id in set(settings.get_admin_ids()):
                        role = "admin"
                    else:
                        role = "user"
                if role is None:
                    role = "user"
        if role != "owner":
            first = args[0] if args else None
            if isinstance(first, CallbackQuery):
                await first.answer("❌ 此操作仅所有者可用", show_alert=True)
                return None
            if isinstance(first, Message):
                await first.answer("❌ 此操作仅所有者可用")
                return None
            return None
        return await func(*args, **kwargs)

    return wrapper


def require_admin_priv(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """管理员或所有者权限装饰器

    功能说明:
    - 在调用处理器前检查 `role` 是否为 "admin" 或 "owner"

    输入参数:
    - func: 需要保护的异步处理器函数

    返回值:
    - Callable[..., Awaitable[Any]]: 包装后的处理器函数
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        role: str | None = kwargs.get("role")
        if role is None:
            session: AsyncSession | None = kwargs.get("session")
            user_id: int | None = None
            first = args[0] if args else None
            if (isinstance(first, CallbackQuery) and first.from_user) or (isinstance(first, Message) and first.from_user):
                user_id = first.from_user.id
            if session and user_id is not None:
                result = await session.execute(
                    select(UserExtendModel.role).where(UserExtendModel.user_id == user_id)
                )
                r = result.scalar_one_or_none()
                if r == UserRole.owner:
                    role = "owner"
                elif r == UserRole.admin:
                    role = "admin"
                else:
                    role = "user"
            else:
                with contextlib.suppress(Exception):
                    if user_id is not None and user_id == settings.get_owner_id():
                        role = "owner"
                    elif user_id is not None and user_id in set(settings.get_admin_ids()):
                        role = "admin"
                    else:
                        role = "user"
                if role is None:
                    role = "user"
        if role not in {"admin", "owner"}:
            first = args[0] if args else None
            if isinstance(first, CallbackQuery):
                await first.answer("❌ 此操作仅限管理员或所有者", show_alert=True)
                return None
            if isinstance(first, Message):
                await first.answer("❌ 此操作仅限管理员或所有者")
                return None
            return None
        return await func(*args, **kwargs)

    return wrapper
