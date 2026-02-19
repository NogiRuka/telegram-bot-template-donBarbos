"""
群组成员事件处理模块

功能:
- 监听成员离开/被踢出事件
- 自动触发 Emby 账号清理 (同 /ban 逻辑)
- 记录审计日志
"""
from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import Chat, ChatMemberUpdated, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models import GroupType
from bot.handlers.group.group_message_saver import message_saver
from bot.services.admin_service import ban_emby_user
from bot.services.group_config_service import get_or_create_group_config
from bot.services.users import upsert_user_on_interaction
from bot.utils.msg_group import send_group_notification
from bot.utils.text import escape_markdown_v2

router = Router(name="group_member_events")


def _is_config_group(chat: Chat) -> bool:
    if not settings.GROUP:
        return True
    try:
        if chat.id == int(settings.GROUP):
            return True
    except (ValueError, TypeError):
        pass
    if chat.username:
        config_group = settings.GROUP.lstrip("@").lower()
        event_group = chat.username.lower()
        if config_group == event_group:
            return True
    return False


@router.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]) & F.new_chat_members)
async def delete_join_message(message: Message, session: AsyncSession) -> None:
    try:
        group_type = GroupType.SUPERGROUP if message.chat.type == ChatType.SUPERGROUP else GroupType.GROUP
        config = await get_or_create_group_config(
            session=session,
            chat_id=message.chat.id,
            chat_title=message.chat.title,
            chat_username=message.chat.username,
            group_type=group_type,
            configured_by_user_id=message.from_user.id if message.from_user else 0,
        )
        if config.is_save_enabled():
            saved = await message_saver.save_message(message, config, session)
            if saved:
                logger.info(
                    f"💾 入群服务消息已保存: chat={message.chat.id}, "
                    f"message_id={message.message_id}"
                )
        await message.delete()
        logger.info(
            f"🧹 已删除入群提示消息: chat={message.chat.id}, "
            f"message_id={message.message_id}, "
            f"new_chat_members={[u.id for u in message.new_chat_members]}, "
            f"text={message.text}"
        )
    except Exception as e:
        logger.warning(f"⚠️ 删除入群提示消息失败: chat={message.chat.id}, message_id={message.message_id}, error={e}")

@router.chat_member(F.new_chat_member.status == ChatMemberStatus.MEMBER)
async def on_member_join(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """
    监听群成员加入事件
    """
    logger.info(f"👤 成员加入事件: chat={event.chat.id}, user={event.new_chat_member.user.id}")
    await upsert_user_on_interaction(session, event.new_chat_member.user)
    if not _is_config_group(event.chat):
        return
    user = event.new_chat_member.user
    user_info = {
        "group_name": event.chat.title,
        "chat_id": event.chat.id,
        "chat_username": event.chat.username,
        "username": user.username if user.username else "",
        "full_name": user.full_name,
        "action": "Join",
        "user_id": str(user.id),
    }

    join_reason = "加入了群组"
    if event.from_user and event.from_user.id != user.id:
        # 如果邀请人是 nmBot，则不发送通知
        if event.from_user.full_name == "nmBot" or event.from_user.first_name == "nmBot":
            return

        inviter_name = escape_markdown_v2(event.from_user.full_name)
        join_reason = f"被 {inviter_name} 邀请加入群组"

    await send_group_notification(
        event.bot,
        user_info,
        join_reason
    )


@router.chat_member(
    F.old_chat_member.status.in_(
        {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.RESTRICTED,
        }
    )
    & F.new_chat_member.status.in_({ChatMemberStatus.LEFT, ChatMemberStatus.KICKED})
)
async def on_member_leave_or_kick(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """
    监听群成员离开或被踢出事件
    """
    logger.info(f"🔄 成员变动事件: chat={event.chat.id}, user={event.new_chat_member.user.id}, old={event.old_chat_member.status}, new={event.new_chat_member.status}")

    if settings.GROUP and not _is_config_group(event.chat):
        logger.warning(f"⚠️ 群组不匹配，忽略事件: config={settings.GROUP}, event_chat={event.chat.id}/{event.chat.username}")
        return

    user = event.new_chat_member.user
    logger.info(f"🚪 用户离开/被踢出: {user.id} ({user.full_name}) - 状态: {event.new_chat_member.status}")

    # 确定操作原因和执行者
    reason = "主动离开了群组"
    admin_id = None

    if event.new_chat_member.status == ChatMemberStatus.KICKED:
        reason = "被管理员踢出/封禁"
        # 尝试获取执行踢出的管理员 (如果有)
        if event.from_user:
             admin_id = event.from_user.id
             reason = f"被管理员 {event.from_user.full_name} 踢出/封禁"

    # 执行清理逻辑
    try:
        user_info = {
            "group_name": event.chat.title,
            "chat_id": event.chat.id,
            "chat_username": event.chat.username,
            "username": user.username if user.username else "",
            "full_name": user.full_name,
            "action": "Kick" if event.new_chat_member.status == ChatMemberStatus.KICKED else "Leave",
            "user_id": str(user.id),
        }

        results = await ban_emby_user(
            session=session,
            target_user_id=user.id,
            admin_id=admin_id,
            reason=reason,
            bot=event.bot,
            user_info=user_info
        )

        logger.info(f"🧼 自动清理 Emby 账号执行结果: {user.id} - {results}")

        await session.commit()
    except Exception as e:
        logger.error(f"❌ 自动清理 Emby 账号失败: {user.id} - {e}")
