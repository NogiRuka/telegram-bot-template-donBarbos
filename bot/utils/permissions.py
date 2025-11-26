from __future__ import annotations
import functools
from typing import TYPE_CHECKING, Any

from aiogram.types import CallbackQuery, Message

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


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
        role: str = kwargs.get("role", "user")
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
        role: str = kwargs.get("role", "user")
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
