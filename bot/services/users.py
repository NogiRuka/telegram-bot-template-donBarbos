from __future__ import annotations
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import func, select, update

from bot.cache import build_key, cached, clear_cache
from bot.core.config import settings
from bot.database.models import UserExtendModel, UserHistoryModel, UserModel, UserRole
from bot.utils.datetime import now

if TYPE_CHECKING:
    from aiogram.types import User
    from sqlalchemy.ext.asyncio import AsyncSession


async def add_user(session: AsyncSession, user: User) -> None:
    """新增用户

    功能说明:
    - 将 aiogram `User` 写入 `users` 表；保存核心字段
    - 额外保存 `is_bot`、`is_premium`、`added_to_attachment_menu`
    - 提交后更新缓存

    输入参数:
    - session: 异步数据库会话
    - user: aiogram User 实例

    返回值:
    - None
    """
    try:
        user_id: int = user.id

        def _normalize_bool(val: bool | None) -> bool | None:
            """布尔值归一化

            功能说明:
            - 将 None 保持为 None；非 None 转为 bool

            输入参数:
            - val: 布尔或 None

            返回值:
            - bool | None
            """
            return bool(val) if val is not None else None

        new_user = UserModel(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=_normalize_bool(getattr(user, "is_premium", None)),
            is_bot=bool(user.is_bot),
            added_to_attachment_menu=_normalize_bool(getattr(user, "added_to_attachment_menu", None)),
        )
        session.add(new_user)
        # 同步写入 user_extend（首次交互）

        ext_res = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user.id))
        ext = ext_res.scalar_one_or_none()
        if ext is None:
            session.add(
                UserExtendModel(
                    user_id=user.id,
                    last_interaction_at=now(),
                )
            )
        await session.commit()
        await clear_cache(user_exists, user_id)
    except Exception:
        # 降级：若失败则忽略新增
        pass


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


async def get_user(session: AsyncSession, user_id: int) -> UserModel | None:
    """根据 ID 获取用户模型实例

    功能说明:
    - 查询数据库获取完整的用户模型对象

    输入参数:
    - session: 异步数据库会话
    - user_id: 用户 ID

    返回值:
    - UserModel | None: 用户模型实例，若不存在返回 None
    """
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()
