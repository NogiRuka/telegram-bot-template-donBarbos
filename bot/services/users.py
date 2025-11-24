from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update

from bot.cache import build_key, cached, clear_cache
from bot.database.models import UserModel

if TYPE_CHECKING:
    from aiogram.types import User
    from sqlalchemy.ext.asyncio import AsyncSession


async def add_user(
    session: AsyncSession,
    user: User,
) -> None:
    """Add a new user to the database."""
    user_id: int = user.id
    first_name: str = user.first_name
    last_name: str | None = user.last_name
    username: str | None = user.username
    language_code: str | None = user.language_code
    is_premium: bool = user.is_premium or False

    new_user = UserModel(
        id=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        language_code=language_code,
        is_premium=is_premium,
    )

    session.add(new_user)
    await session.commit()
    await clear_cache(user_exists, user_id)


@cached(key_builder=lambda session, user_id: build_key(user_id))
async def user_exists(session: AsyncSession, user_id: int) -> bool:
    """Checks if the user is in the database."""
    query = select(UserModel.id).filter_by(id=user_id).limit(1)

    result = await session.execute(query)

    user = result.scalar_one_or_none()
    return bool(user)


@cached(key_builder=lambda session, user_id: build_key(user_id))
async def get_first_name(session: AsyncSession, user_id: int) -> str:
    query = select(UserModel.first_name).filter_by(id=user_id)

    result = await session.execute(query)

    first_name = result.scalar_one_or_none()
    return first_name or ""



    await session.commit()
    return None


@cached(key_builder=lambda session, user_id: build_key(user_id))
async def is_admin(session: AsyncSession, user_id: int) -> bool:
    query = select(UserModel.is_admin).filter_by(id=user_id)

    result = await session.execute(query)

    is_admin = result.scalar_one_or_none()
    return bool(is_admin)


async def set_is_admin(session: AsyncSession, user_id: int, is_admin: bool) -> None:
    stmt = update(UserModel).where(UserModel.id == user_id).values(is_admin=is_admin)

    await session.execute(stmt)
    await session.commit()


async def add_admin(session: AsyncSession, user_id: int) -> bool:
    """添加管理员

    功能说明:
    - 将指定用户的管理员标志设置为 True

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID

    返回值:
    - bool: True 表示操作成功
    """
    try:
        await set_is_admin(session, user_id, True)
        return True
    except Exception:
        return False


async def remove_admin(session: AsyncSession, user_id: int) -> bool:
    """移除管理员

    功能说明:
    - 将指定用户的管理员标志设置为 False

    输入参数:
    - session: 异步数据库会话
    - user_id: Telegram 用户ID

    返回值:
    - bool: True 表示操作成功
    """
    try:
        await set_is_admin(session, user_id, False)
        return True
    except Exception:
        return False


@cached(key_builder=lambda session: build_key())
async def get_all_users(session: AsyncSession) -> list[UserModel]:
    query = select(UserModel)

    result = await session.execute(query)

    users = result.scalars()
    return list(users)


@cached(key_builder=lambda session: build_key())
async def get_user_count(session: AsyncSession) -> int:
    query = select(func.count()).select_from(UserModel)

    result = await session.execute(query)

    count = result.scalar_one_or_none() or 0
    return int(count)


@cached(key_builder=lambda session: build_key())
async def list_admins(session: AsyncSession) -> list[UserModel]:
    """列出管理员用户

    功能说明:
    - 查询所有 `is_admin=True` 的用户列表

    输入参数:
    - session: 异步数据库会话

    返回值:
    - list[UserModel]: 管理员列表
    """
    query = select(UserModel).where(UserModel.is_admin)
    result = await session.execute(query)
    users = result.scalars()
    return list(users)
