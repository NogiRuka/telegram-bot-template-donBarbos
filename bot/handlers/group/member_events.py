"""
群组成员事件处理模块

功能:
- 监听成员离开/被踢出事件
- 自动触发 Emby 账号清理 (同 /ban 逻辑)
- 记录审计日志
"""
from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.types import ChatMemberUpdated
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.services.admin_service import ban_emby_user
from bot.services.users import upsert_user_on_interaction

router = Router(name="group_member_events")


from bot.utils.msg_group import send_group_notification

@router.chat_member(F.new_chat_member.status == ChatMemberStatus.MEMBER)
async def on_member_join(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """
    监听群成员加入事件
    """
    logger.info(f"收到成员加入事件: chat={event.chat.id}, user={event.new_chat_member.user.id}")
    # 保存用户信息
    await upsert_user_on_interaction(session, event.new_chat_member.user)

    # 仅处理配置的群组
    if settings.GROUP:
        is_match = False
        try:
            if event.chat.id == int(settings.GROUP):
                is_match = True
        except (ValueError, TypeError):
            pass
        
        if not is_match and event.chat.username:
            config_group = settings.GROUP.lstrip("@").lower()
            event_group = event.chat.username.lower()
            if config_group == event_group:
                is_match = True
        
        if not is_match:
            return

    # 发送加入通知到管理员群组
    user = event.new_chat_member.user
    user_info = {
        "group_name": event.chat.title,
        "username": user.username if user.username else "Unknown",
        "full_name": user.full_name,
        "action": "Join",
        "user_id": str(user.id)
    }
    
    await send_group_notification(
        event.bot, 
        user_info, 
        f"用户 {user.full_name} 加入了群组 {event.chat.title}"
    )


@router.chat_member(F.old_chat_member.status.in_({ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.RESTRICTED}) & F.new_chat_member.status.in_({ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}))
async def on_member_leave_or_kick(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """
    监听群成员离开或被踢出事件
    """
    logger.info(f"收到成员变动事件: chat={event.chat.id}, user={event.new_chat_member.user.id}, old={event.old_chat_member.status}, new={event.new_chat_member.status}")

    # 仅处理配置的群组
    if settings.GROUP:
        is_match = False
        # 1. 尝试匹配 Chat ID
        try:
            if event.chat.id == int(settings.GROUP):
                is_match = True
        except (ValueError, TypeError):
            pass
        
        # 2. 尝试匹配 Username (忽略大小写)
        if not is_match and event.chat.username:
            # settings.GROUP 可能是 @username，移除 @ 后对比
            config_group = settings.GROUP.lstrip("@").lower()
            event_group = event.chat.username.lower()
            if config_group == event_group:
                is_match = True
        
        if not is_match:
            logger.warning(f"群组不匹配，忽略事件: config={settings.GROUP}, event_chat={event.chat.id}/{event.chat.username}")
            return

    user = event.new_chat_member.user
    logger.info(f"监测到用户离开/被踢出: {user.id} ({user.full_name}) - 状态: {event.new_chat_member.status}")

    # 确定操作原因和执行者
    reason = "用户主动离开群组"
    admin_id = None
    
    if event.new_chat_member.status == ChatMemberStatus.KICKED:
        reason = "用户被管理员踢出/封禁"
        # 尝试获取执行踢出的管理员 (如果有)
        if event.from_user:
             admin_id = event.from_user.id
             reason = f"用户被管理员 {event.from_user.full_name} ({admin_id}) 踢出/封禁"

    # 执行清理逻辑
    try:
        user_info = {
            "group_name": event.chat.title,
            "username": user.username if user.username else "Unknown",
            "full_name": user.full_name,
            "action": "Kick" if event.new_chat_member.status == ChatMemberStatus.KICKED else "Leave"
        }
        
        results = await ban_emby_user(
            session=session,
            target_user_id=user.id,
            admin_id=admin_id,
            reason=reason,
            bot=event.bot,
            user_info=user_info
        )
        
        logger.info(f"自动清理 Emby 账号执行结果: {user.id} - {results}")
        
        await session.commit()
    except Exception as e:
        logger.error(f"自动清理 Emby 账号失败: {user.id} - {e}")
