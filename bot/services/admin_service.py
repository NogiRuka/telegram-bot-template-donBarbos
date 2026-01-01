"""
管理员服务模块

提供管理员操作的核心业务逻辑，如封禁用户、清理数据等。
"""
import html
from typing import Optional

from aiogram import Bot
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models import (
    ActionType,
    AuditLogModel,
    EmbyUserModel,
    UserExtendModel,
)
from bot.utils.datetime import now
from bot.utils.emby import get_emby_client
from bot.utils.msg_group import send_group_notification


async def ban_emby_user(
    session: AsyncSession,
    target_user_id: int,
    admin_id: Optional[int] = None,
    reason: str = "封禁",
    bot: Optional[Bot] = None,
    user_info: Optional[dict[str, str]] = None,
) -> list[str]:
    """
    封禁 Emby 用户逻辑
    
    功能:
    1. 删除 Emby 账号 (API)
    2. 软删除数据库 Emby 用户数据
    3. 记录审计日志
    4. 发送通知到管理员群组 (如果配置)
    
    Args:
        session: 数据库会话
        target_user_id: 目标 Telegram 用户 ID
        admin_id: 执行操作的管理员 ID (可选)
        reason: 封禁原因
        bot: Bot 实例 (用于发送通知)
        user_info: 用户信息字典 (username, full_name, group_name 等)
        
    Returns:
        操作结果消息列表
    """
    results = []
    
    # 查找 Emby 关联
    stmt = select(UserExtendModel).where(UserExtendModel.user_id == target_user_id)
    result = await session.execute(stmt)
    user_extend = result.scalar_one_or_none()

    emby_user_id = None
    if not user_extend or not user_extend.emby_user_id:
        results.append("ℹ️ 该用户未绑定 Emby 账号")
    else:
        emby_user_id = user_extend.emby_user_id

    deleted_by = admin_id if admin_id else 0  # 0 表示系统或未知

    # 1. 删除 Emby 账号 (API)
    if emby_user_id:
        emby_client = get_emby_client()
        if emby_client:
            try:
                await emby_client.delete_user(emby_user_id)
                results.append(f"✅ Emby 账号已删除 (ID: {emby_user_id})")
            except Exception as e:
                logger.error(f"删除 Emby 账号失败: {e}")
                results.append(f"❌ Emby 账号删除失败: {e}")
        else:
            results.append("⚠️ 未配置 Emby API，跳过账号删除")

    # 2. 软删除数据库 EmbyUserModel
    if emby_user_id:
        stmt_emby = select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id)
        result_emby = await session.execute(stmt_emby)
        emby_user = result_emby.scalar_one_or_none()

        if emby_user:
            # 如果已经被删除了，就不重复记录了，但还是要记录审计日志
            if not emby_user.is_deleted:
                emby_user.is_deleted = True
                emby_user.deleted_at = now()
                emby_user.deleted_by = deleted_by
                emby_user.remark = f"{reason} (操作者: {deleted_by})"
                results.append("✅ Emby 用户数据已标记为删除")
            else:
                 results.append("ℹ️ Emby 用户数据已是删除状态")
        else:
            results.append("⚠️ 未找到本地 Emby 用户数据")

    # 3. 记录审计日志
    audit_log = AuditLogModel(
        user_id=deleted_by,
        action_type=ActionType.USER_BLOCK,  # 使用 USER_BLOCK 作为封禁/移除的操作类型
        target_id=str(target_user_id),
        description=f"封禁用户 {target_user_id}",  # 必填字段
        details={
            "emby_user_id": emby_user_id,
            "reason": reason,
            "results": results,
            "source": "auto_ban_on_leave" if not admin_id else "manual_ban"
        },
        ip_address="127.0.0.1", # 内部操作
        user_agent="System/Bot"
    )
    session.add(audit_log)

    # 4. 发送通知到管理员群组
    if bot and user_info:
        # 确保 user_id 存在
        user_info["user_id"] = str(target_user_id)
        # 调用通用通知函数
        await send_group_notification(bot, user_info, reason)

    return results


async def unban_user_service(
    session: AsyncSession,
    target_user_id: int,
    admin_id: Optional[int] = None,
    reason: str = "解封",
    bot: Optional[Bot] = None,
    user_info: Optional[dict[str, str]] = None,
) -> list[str]:
    """
    解封用户服务逻辑
    
    功能:
    1. 记录审计日志
    2. 发送通知到管理员群组
    
    Args:
        session: 数据库会话
        target_user_id: 目标 Telegram 用户 ID
        admin_id: 执行操作的管理员 ID
        reason: 解封原因
        bot: Bot 实例
        user_info: 用户信息字典
        
    Returns:
        操作结果消息列表
    """
    results = []
    operator_id = admin_id if admin_id else 0
    
    # 记录审计日志
    audit_log = AuditLogModel(
        user_id=operator_id,
        action_type=ActionType.USER_UNBLOCK,
        target_id=str(target_user_id),
        description=f"解封用户 {target_user_id}",  # 必填字段
        details={
            "reason": reason,
            "source": "manual_unban"
        },
        ip_address="127.0.0.1",
        user_agent="System/Bot"
    )
    session.add(audit_log)
    results.append("✅ 已记录解封审计日志")
    
    # 发送通知到管理员群组
    if bot and user_info:
        user_info["user_id"] = str(target_user_id)
        await send_group_notification(bot, user_info, reason)
            
    return results
