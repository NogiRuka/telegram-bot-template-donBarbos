"""
封禁用户命令模块
"""
from datetime import datetime

from aiogram import Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.services.admin_service import ban_emby_user
from bot.utils.decorators import private_chat_only

router = Router(name="command_ban")


def is_global_admin(user_id: int) -> bool:
    """检查用户是否为全局管理员 (Owner 或 Admin)"""
    if user_id == settings.OWNER_ID:
        return True
    if settings.ADMIN_IDS:
        try:
            admin_ids = [int(x.strip()) for x in settings.ADMIN_IDS.split(",") if x.strip() and x.strip().isdigit()]
            return user_id in admin_ids
        except Exception:
            return False
    return False


@router.message(Command("ban"))
@private_chat_only
async def ban_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    封禁用户命令

    功能:
    1. 从群组移除用户
    2. 删除 Emby 账号 (如果存在)
    3. 软删除数据库中的 Emby 用户数据

    用法: /ban <telegram_user_id>
    """
    # 权限检查
    is_authorized = False
    
    # 如果在群组中，检查是否为群管理员
    if message.chat.type in ["group", "supergroup"]:
        member = await message.chat.get_member(message.from_user.id)
        if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
            is_authorized = True
    
    # 全局管理员或私聊情况下的检查
    if not is_authorized and is_global_admin(message.from_user.id):
        is_authorized = True
        
    if not is_authorized:
        await message.reply("❌ 您没有权限执行此操作")
        return

    if not command.args:
        await message.reply("⚠️ 请提供 Telegram 用户 ID\n用法: `/ban <user_id>`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(command.args)
    except ValueError:
        await message.reply("❌ 无效的用户 ID，必须为数字")
        return

    results = []

    # 1. 从群组移除
    if settings.GROUP:
        try:
            # 尝试踢出成员 (ban_chat_member 会踢出并拉黑)
            await message.bot.ban_chat_member(chat_id=settings.GROUP, user_id=target_user_id)
            results.append("✅ 已从群组移除并封禁")
        except Exception as e:
            logger.warning(f"无法从群组移除用户 {target_user_id}: {e}")
            results.append(f"⚠️ 无法从群组移除: {e}")
    else:
        results.append("ℹ️ 未配置群组，跳过群组移除")

    # 2. 调用封禁服务 (Emby 账号删除 + 软删除 + 审计日志)
    # 尝试获取群组信息
    group_name = "Private"
    if message.chat.type != "private":
        group_name = message.chat.title
    elif settings.GROUP:
        # 如果是私聊但配置了群组，尝试获取群组名称（需要API调用，暂用ID代替或标记Manual）
        group_name = f"Group{settings.GROUP}"

    # 尝试获取目标用户信息
    # 查询数据库获取用户信息
    from bot.database.models import UserModel
    from sqlalchemy import select

    db_user_result = await session.execute(select(UserModel).where(UserModel.id == target_user_id))
    db_user = db_user_result.scalar_one_or_none()

    if db_user:
        user_info = {
            "group_name": group_name,
            "username": f"@{db_user.username}" if db_user.username else "Unknown",
            "full_name": db_user.get_full_name(),
            "action": "ManualBan"
        }
    else:
        # 如果数据库中没有，尝试通过 get_chat_member 获取（如果机器人在该群组）
        try:
            if settings.GROUP:
                chat_member = await message.bot.get_chat_member(chat_id=settings.GROUP, user_id=target_user_id)
                user = chat_member.user
                full_name = user.full_name
                username = f"@{user.username}" if user.username else "Unknown"
                user_info = {
                    "group_name": group_name,
                    "username": username,
                    "full_name": full_name,
                    "action": "ManualBan"
                }
            else:
                raise Exception("No group configured")
        except Exception:
            # 最后的后备方案
            user_info = {
                "group_name": group_name,
                "username": "Unknown",
                "full_name": "Unknown",
                "action": "ManualBan"
            }

    emby_results = await ban_emby_user(
        session=session,
        target_user_id=target_user_id,
        admin_id=message.from_user.id,
        reason="管理员手动封禁",
        bot=message.bot,
        user_info=user_info
    )
    results.extend(emby_results)

    await session.commit()
    
    # 构建按钮
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔓 解除封禁", callback_data=f"unban:{target_user_id}"),
            InlineKeyboardButton(text="❌ 关闭", callback_data="close_message")
        ]
    ])
    
    await message.reply("\n".join(results), reply_markup=kb)
