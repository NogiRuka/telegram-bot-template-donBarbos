from __future__ import annotations
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    GroupConfigModel,
    GroupType,
    MessageModel,
    MessageSaveMode,
)


async def get_or_create_group_config(
    session: AsyncSession,
    chat_id: int,
    chat_title: Optional[str],
    chat_username: Optional[str],
    group_type: GroupType,
    configured_by_user_id: int,
) -> GroupConfigModel:
    """
    获取或创建群组消息保存配置

    功能说明：
    - 尝试获取指定群组的配置，若不存在则按默认值创建并持久化

    输入参数：
    - session: 异步数据库会话
    - chat_id: 群组ID
    - chat_title: 群组标题
    - chat_username: 群组用户名
    - group_type: 群组类型枚举
    - configured_by_user_id: 配置操作者的用户ID

    返回值：
    - GroupConfigModel: 群组配置对象
    """
    result = await session.execute(
        select(GroupConfigModel).where(
            GroupConfigModel.chat_id == chat_id,
            GroupConfigModel.is_deleted == False,
        )
    )
    config = result.scalar_one_or_none()
    if config:
        return config

    config = GroupConfigModel.create_for_group(
        chat_id=chat_id,
        chat_title=chat_title,
        chat_username=chat_username,
        group_type=group_type,
        configured_by_user_id=configured_by_user_id,
    )
    session.add(config)
    await session.commit()
    return config


async def get_group_message_stats(session: AsyncSession, chat_id: int) -> int:
    """
    获取群组消息统计数量

    功能说明：
    - 统计指定群组的未删除消息总数

    输入参数：
    - session: 异步数据库会话
    - chat_id: 群组ID

    返回值：
    - int: 消息总数
    """
    stats_result = await session.execute(
        select(func.count(MessageModel.id)).where(
            MessageModel.chat_id == chat_id,
            MessageModel.is_deleted == False,
        )
    )
    return int(stats_result.scalar() or 0)


async def toggle_save_enabled(session: AsyncSession, config: GroupConfigModel) -> GroupConfigModel:
    """
    切换消息保存启用状态

    功能说明：
    - 启用或禁用消息保存；同时确保保存模式与状态一致

    输入参数：
    - session: 异步数据库会话
    - config: 群组配置对象

    返回值：
    - GroupConfigModel: 更新后的配置对象
    """
    config.is_message_save_enabled = not config.is_message_save_enabled
    if config.is_message_save_enabled and config.message_save_mode == MessageSaveMode.DISABLED:
        config.message_save_mode = MessageSaveMode.ALL
    elif not config.is_message_save_enabled:
        config.message_save_mode = MessageSaveMode.DISABLED
    await session.commit()
    return config


async def set_save_mode(
    session: AsyncSession,
    config: GroupConfigModel,
    mode: MessageSaveMode,
) -> GroupConfigModel:
    """
    设置消息保存模式

    功能说明：
    - 更新保存模式并同步启用状态

    输入参数：
    - session: 异步数据库会话
    - config: 群组配置对象
    - mode: 保存模式枚举

    返回值：
    - GroupConfigModel: 更新后的配置对象
    """
    config.message_save_mode = mode
    config.is_message_save_enabled = mode != MessageSaveMode.DISABLED
    await session.commit()
    return config


async def soft_delete_messages_by_chat(session: AsyncSession, chat_id: int) -> int:
    """
    软删除群组的所有消息

    功能说明：
    - 标记指定群组的未删除消息为软删除，返回删除数量

    输入参数：
    - session: 异步数据库会话
    - chat_id: 群组ID

    返回值：
    - int: 被软删除的消息数量
    """
    messages_result = await session.execute(
        select(MessageModel).where(
            MessageModel.chat_id == chat_id,
            MessageModel.is_deleted == False,
        )
    )
    messages = messages_result.scalars().all()
    deleted_count = 0
    for message in messages:
        message.soft_delete()
        deleted_count += 1
    await session.commit()
    return deleted_count
