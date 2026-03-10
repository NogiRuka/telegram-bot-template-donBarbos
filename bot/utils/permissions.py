from __future__ import annotations
import contextlib
import functools
from typing import TYPE_CHECKING, Any

from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy import select

from bot.core.config import settings
from bot.database.models import UserExtendModel, UserRole
from bot.services.config_service import get_config, is_command_enabled

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram import Bot
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
    - 仅从数据库 `user_extend.role` 解析
    - 若无会话或无记录, 默认返回 user

    输入参数:
    - session: 异步数据库会话, 可为 None
    - user_id: Telegram 用户ID, 可为 None

    返回值:
    - str: 角色标识, 取值为 "owner" | "admin" | "user"
    """
    if session and user_id is not None:
        with contextlib.suppress(Exception):
            result = await session.execute(select(UserExtendModel.role).where(UserExtendModel.user_id == user_id))
            r = result.scalar_one_or_none()
            if r == UserRole.owner:
                return "owner"
            if r == UserRole.admin:
                return "admin"
    return "user"


async def is_group_admin(bot: Bot, user_id: int) -> bool:
    """检查用户是否为群组管理员

    功能说明:
    - 检查用户是否在配置的群组(settings.GROUP)中拥有管理员或创建者权限

    输入参数:
    - bot: Bot 实例
    - user_id: 用户 ID

    返回值:
    - bool: 是否为管理员
    """
    if not settings.GROUP:
        return False

    try:
        from aiogram.enums import ChatMemberStatus
        member = await bot.get_chat_member(chat_id=settings.GROUP, user_id=user_id)
        return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)
    except Exception as e:
        logger.warning(f"⚠️ 检查群组管理员权限失败 (user_id={user_id}): {e}")
        return False


async def check_user_in_group(bot: Bot, user_id: int) -> bool:
    """
    检查用户是否在配置的群组中

    Args:
        bot: Bot实例
        user_id: 用户ID

    Returns:
        bool: 是否在群组中
    """
    if not settings.GROUP:
        return True

    target_group = settings.GROUP
    # 如果不是数字ID且不以@开头，尝试添加@
    if not str(target_group).lstrip("-").isdigit() and not target_group.startswith("@"):
        target_group = f"@{target_group}"

    try:
        member = await bot.get_chat_member(chat_id=target_group, user_id=user_id)
        # 成员状态：creator, administrator, member, restricted (被限制但仍在群内)
        return member.status in ("creator", "administrator", "member", "restricted")
    except Exception as e:
        logger.warning(f"⚠️ 检查群组成员身份失败 (user_id={user_id}, group={target_group}): {e}")
        return False


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
                await first.answer("🔴 此操作仅所有者可用", show_alert=True)
                return None
            if isinstance(first, Message):
                await first.answer("🔴 此操作仅所有者可用")
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
                await first.answer("🔴 此操作仅限管理员或所有者", show_alert=True)
                return None
            if isinstance(first, Message):
                await first.answer("🔴 此操作仅限管理员或所有者")
                return None
            return None
        return await func(*args, **kwargs)

    return wrapper


def require_admin_feature(feature_key: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """管理员功能开关装饰器

    功能说明:
    - 在调用处理器前检查管理员功能是否开启(总开关与具体功能键)

    输入参数:
    - feature_key: 配置键名, 例如 "admin.groups"、"admin.stats"

    返回值:
    - Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]: 装饰器函数
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            session: AsyncSession | None = kwargs.get("session")
            first = args[0] if args else None
            if session is None:
                return await func(*args, **kwargs)
            enabled_all = bool(await get_config(session, "admin.features.enabled") or False)
            enabled_feature = bool(await get_config(session, feature_key) or False)
            if enabled_all and enabled_feature:
                return await func(*args, **kwargs)
            if isinstance(first, CallbackQuery):
                await first.answer("🔴 功能已关闭", show_alert=True)
                return None
            if isinstance(first, Message):
                await first.answer("🔴 功能已关闭")
                return None
            return None

        return wrapper

    return decorator



def require_user_feature(feature_key: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    """用户功能开关装饰器

    功能说明:
    - 在处理用户功能前检查用户总开关与具体功能是否启用
    - 所有者 (Owner) 豁免检查，直接通过

    输入参数:
    - feature_key: 配置键名, 例如 "user.register"、"user.info"

    返回值:
    - Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]: 装饰器函数
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            session: AsyncSession | None = kwargs.get("session")
            first = args[0] if args else None

            # 1. 提取用户ID
            user_id = _extract_user_id(first)

            # 2. 检查是否为所有者 (豁免检查)
            if session is not None and user_id is not None:
                role = await _resolve_role(session, user_id)
                if role == "owner":
                    return await func(*args, **kwargs)

            # 3. 检查功能开关
            if session is None:
                return await func(*args, **kwargs)
            enabled_all = bool(await get_config(session, "user.features.enabled") or False)
            enabled_feature = bool(await get_config(session, feature_key) or False)
            if enabled_all and enabled_feature:
                return await func(*args, **kwargs)
            if isinstance(first, CallbackQuery):
                await first.answer("🔴 功能已关闭", show_alert=True)
                return None
            if isinstance(first, Message):
                await first.answer("🔴 功能已关闭")
                return None
            return None

        return wrapper

    return decorator


def require_emby_account(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """要求用户绑定 Emby 账号装饰器

    功能说明:
    - 检查用户是否已绑定 Emby 账号
    - 未绑定则提示错误

    输入参数:
    - func: 需要保护的异步处理器函数

    返回值:
    - Callable[..., Awaitable[Any]]: 包装后的处理器函数
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        session: AsyncSession | None = kwargs.get("session")
        first = args[0] if args else None
        user_id = _extract_user_id(first)

        if session and user_id:
            # 检查 UserExtendModel 是否有 emby_user_id
            stmt = select(UserExtendModel.emby_user_id).where(UserExtendModel.user_id == user_id)
            result = await session.execute(stmt)
            emby_user_id = result.scalar_one_or_none()

            if not emby_user_id:
                if isinstance(first, CallbackQuery):
                    await first.answer("❌ 未绑定 Emby 账号", show_alert=True)
                    return None
                if isinstance(first, Message):
                    await first.answer("❌ 未绑定 Emby 账号")
                    return None
                return None

        return await func(*args, **kwargs)

    return wrapper


def require_command_access(scope: str, name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            session: AsyncSession | None = kwargs.get("session")
            first = args[0] if args else None
            if session is None:
                return await func(*args, **kwargs)
            enabled = await is_command_enabled(session, scope, name)
            if enabled:
                return await func(*args, **kwargs)
            if isinstance(first, CallbackQuery):
                await first.answer("🔴 此命令已关闭", show_alert=True)
                return None
            if isinstance(first, Message):
                await first.answer("🔴 此命令已关闭")
                return None
            return None

        return wrapper

    return decorator


def require_user_command_access(name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    return require_command_access("user", name)


def require_admin_command_access(name: str) -> Callable[[Callable[..., Awaitable[Any]]], Callable[..., Awaitable[Any]]]:
    return require_command_access("admin", name)
