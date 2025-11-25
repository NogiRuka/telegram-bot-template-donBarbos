from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import func, select, update

from bot.cache import build_key, cached, clear_cache
from bot.database.models import UserModel, UserHistoryModel, UserExtendModel, UserRole

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
        new_user = UserModel(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=bool(user.is_premium),
            is_bot=bool(user.is_bot),
            added_to_attachment_menu=bool(user.added_to_attachment_menu) if hasattr(user, "added_to_attachment_menu") else None,
        )
        session.add(new_user)
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



    await session.commit()
    return None


@cached(key_builder=lambda session, user_id: build_key(user_id))
async def is_admin(session: AsyncSession, user_id: int) -> bool:
    """判断是否管理员

    功能说明:
    - 基于 `user_extend.role` 判断是否具备管理员权限（含 owner）

    输入参数:
    - session: 异步数据库会话
    - user_id: 用户 ID

    返回值:
    - bool: True 表示管理员或所有者
    """
    query = select(UserExtendModel.role).where(UserExtendModel.user_id == user_id)
    result = await session.execute(query)
    role = result.scalar_one_or_none()
    return role in {UserRole.admin, UserRole.owner}


async def save_user_snapshot(session: AsyncSession, user: User) -> None:
    """保存用户信息快照

    功能说明:
    - 将 aiogram 用户信息保存到 `user_history`，用于历史追踪

    输入参数:
    - session: 异步数据库会话
    - user: aiogram User 实例

    返回值:
    - None
    """
    try:
        snapshot = UserHistoryModel(
            user_id=user.id,
            is_bot=bool(user.is_bot),
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
            is_premium=bool(user.is_premium),
            added_to_attachment_menu=bool(user.added_to_attachment_menu) if hasattr(user, "added_to_attachment_menu") else None,
        )
        session.add(snapshot)
        await session.commit()
    except Exception:
        # 快照失败不影响主流程
        pass


async def upsert_user_on_interaction(session: AsyncSession, user: User) -> None:
    """交互时更新用户信息

    功能说明:
    - 用户与机器人交互（消息/回调）时，更新 `users` 表的最新字段
    - 若用户不存在则创建；存在则覆盖可变字段
    - 更新 `user_extend.last_interaction_at`，必要时自动创建扩展记录
    - 保存一条 `user_history` 快照以便追踪变更

    输入参数:
    - session: 异步数据库会话
    - user: aiogram User 实例

    返回值:
    - None
    """
    try:
        exists = await user_exists(session, user.id)
        if not exists:
            await add_user(session, user)
        else:
            stmt = (
                update(UserModel)
                .where(UserModel.id == user.id)
                .values(
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=user.username,
                    language_code=user.language_code,
                    is_premium=bool(user.is_premium),
                    is_bot=bool(user.is_bot),
                    added_to_attachment_menu=bool(user.added_to_attachment_menu) if hasattr(user, "added_to_attachment_menu") else None,
                )
            )
            await session.execute(stmt)
            await session.commit()

        # 更新扩展表最后交互时间（无则创建）
        ext_res = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user.id))
        ext = ext_res.scalar_one_or_none()
        if ext is None:
            ext = UserExtendModel(user_id=user.id)
            session.add(ext)
        from datetime import datetime
        ext.last_interaction_at = datetime.now()
        await session.commit()

        # 保存快照（失败不影响主流程）
        await save_user_snapshot(session, user)
    except Exception:
        # 忽略更新失败，避免影响交互
        pass


async def set_is_admin(session: AsyncSession, user_id: int, is_admin: bool) -> None:
    """设置管理员角色

    功能说明:
    - 将 `user_extend.role` 设置为 `admin` 或 `user`

    输入参数:
    - session: 异步数据库会话
    - user_id: 用户 ID
    - is_admin: 是否管理员

    返回值:
    - None
    """
    target_role = UserRole.admin if is_admin else UserRole.user
    # upsert
    existing = await session.execute(select(UserExtendModel).where(UserExtendModel.user_id == user_id))
    model = existing.scalar_one_or_none()
    if model:
        # 若当前为 owner，则不降级
        if model.role == UserRole.owner:
            return
        model.role = target_role
    else:
        model = UserExtendModel(user_id=user_id, role=target_role)
        session.add(model)
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
    - 基于 `user_extend.role in ('admin','owner')` 查询管理员/所有者对应的用户列表

    输入参数:
    - session: 异步数据库会话

    返回值:
    - list[UserModel]: 管理员列表
    """
    role_query = select(UserExtendModel.user_id).where(UserExtendModel.role.in_([UserRole.admin, UserRole.owner]))
    query = select(UserModel).where(UserModel.id.in_(role_query))
    result = await session.execute(query)
    users = result.scalars()
    return list(users)
