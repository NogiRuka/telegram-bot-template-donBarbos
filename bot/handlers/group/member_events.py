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

router = Router(name="group_member_events")


@router.chat_member(F.old_chat_member.status.in_({ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}) & F.new_chat_member.status.in_({ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}))
async def on_member_leave_or_kick(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """
    监听群成员离开或被踢出事件
    
    触发条件:
    - 旧状态: MEMBER / ADMINISTRATOR / CREATOR
    - 新状态: LEFT (主动离开) / KICKED (被踢出/封禁)
    
    执行操作:
    - 调用 ban_emby_user 清理 Emby 账号
    """
    # 仅处理配置的群组
    if settings.GROUP and event.chat.id != settings.GROUP:
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
        
        if any("✅" in r for r in results):
            logger.info(f"自动清理 Emby 账号成功: {user.id} - {results}")
            # 可选: 发送通知到群组或日志频道 (这里仅打印日志)
        
        await session.commit()
    except Exception as e:
        logger.error(f"自动清理 Emby 账号失败: {user.id} - {e}")
