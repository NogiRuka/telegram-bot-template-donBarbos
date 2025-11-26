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


def _extract_user_id(first: Any) -> int | None:
    """提取用户ID

    功能说明:
    - 从 `Message`/`CallbackQuery` 中提取 `from_user.id`

    输入参数:
    - first: 处理器第一个位置参数, 通常为 `Message` 或 `CallbackQuery`

    返回值:
    - int | None: 用户ID, 无法提取时返回 None
    """
    if isinstance(first, CallbackQuery) and first.from_user:
        return first.from_user.id
    if isinstance(first, Message) and first.from_user:
        return first.from_user.id
    return None


async def _resolve_role(session: AsyncSession | None, user_id: int | None) -> str:
    """解析角色

    功能说明:
    - 优先从数据库 `user_extend.role` 解析; 若无会话或无记录, 回退到配置

    输入参数:
    - session: 异步数据库会话, 可为 None
    - user_id: Telegram 用户ID, 可为 None

    返回值:
    - str: 角色标识, 取值为 "owner" | "admin" | "user"
    """
    if session and user_id is not None:
        with contextlib.suppress(Exception):
            result = await session.execute(
                select(UserExtendModel.role).where(UserExtendModel.user_id == user_id)
            )
            r = result.scalar_one_or_none()
            if r == UserRole.owner:
                return "owner"
            if r == UserRole.admin:
                return "admin"
            return "user"
    with contextlib.suppress(Exception):
        if user_id is not None and user_id == settings.get_owner_id():
            return "owner"
        if user_id is not None and user_id in set(settings.get_admin_ids()):
            return "admin"
    return "user"


def require_owner(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """所有者权限装饰器

    功能说明:
    - 在调用处理器前检查用户是否为所有者, 否则提示无权限

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
            first = args[0] if args else None
            user_id = _extract_user_id(first)
            role = await _resolve_role(session, user_id)
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
    - 在调用处理器前检查用户是否为管理员或所有者

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
            first = args[0] if args else None
            user_id = _extract_user_id(first)
            role = await _resolve_role(session, user_id)
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
