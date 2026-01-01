"""
解除封禁命令模块
"""
from aiogram import F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.services.admin_service import unban_user_service
from bot.utils.decorators import private_chat_only
from bot.utils.permissions import is_group_admin

router = Router(name="command_unban")


@router.message(Command("unban"))
@private_chat_only
async def unban_user_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """
    解除封禁命令
    用法: /unban <user_id>
    """
    if not await is_group_admin(message.bot, message.from_user.id):
        await message.reply("❌ 仅限群组管理员使用")
        return

    if not command.args:
        await message.reply("⚠️ 请提供 Telegram 用户 ID\n用法: `/unban <user_id>`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(command.args)
    except ValueError:
        await message.reply("❌ 无效的用户 ID，必须为数字")
        return

    await process_unban(message, target_user_id, session, message.from_user.id)


@router.callback_query(F.data.startswith("unban:"))
async def unban_callback(query: CallbackQuery, session: AsyncSession) -> None:
    """处理解除封禁按钮点击"""
    if not await is_group_admin(query.bot, query.from_user.id):
        await query.answer("❌ 无权执行此操作", show_alert=True)
        return

    target_user_id = int(query.data.split(":")[1])
    
    # 修改原消息，避免重复点击
    await query.message.edit_reply_markup(reply_markup=None)
    
    await process_unban(query.message, target_user_id, session, query.from_user.id, is_callback=True)
    await query.answer("已解除封禁")


@router.callback_query(F.data == "close_message")
async def close_callback(query: CallbackQuery, session: AsyncSession) -> None:
    """关闭消息"""
    # 简单的权限检查：只要是群管或原触发者都可以关，这里简化为通用权限检查
    if not await is_group_admin(query.bot, query.from_user.id):
         await query.answer("❌ 无权执行此操作", show_alert=True)
         return
         
    await query.message.delete()


async def process_unban(
    message: Message, 
    target_user_id: int, 
    session: AsyncSession, 
    admin_id: int,
    is_callback: bool = False
) -> None:
    """处理解封核心逻辑"""
    results = []
    
    # 1. Telegram 解封
    if settings.GROUP:
        try:
            # only_if_banned=True: 如果用户没被封，不报错 (但在 aiogram 3.x 某些版本可能不支持此参数，需注意)
            # 查阅 aiogram 3.x 文档，unban_chat_member 支持 only_if_banned
            await message.bot.unban_chat_member(chat_id=settings.GROUP, user_id=target_user_id, only_if_banned=True)
            results.append("✅ 已解除群组封禁")
        except Exception as e:
            logger.warning(f"无法解封用户 {target_user_id}: {e}")
            results.append(f"⚠️ 群组解封失败: {e}")
    else:
        results.append("ℹ️ 未配置群组，跳过群组解封")

    # 2. 记录审计日志并通知
    # 获取群组名称
    group_name = "Private"
    if message.chat.type != "private":
        group_name = message.chat.title
    elif settings.GROUP:
        group_name = f"Group{settings.GROUP}"
        
    user_info = {
        "group_name": group_name,
        "username": "Unknown",
        "full_name": "Unknown",
        "action": "ManualUnban"
    }

    service_results = await unban_user_service(
        session=session,
        target_user_id=target_user_id,
        admin_id=admin_id,
        reason="管理员手动解封",
        bot=message.bot,
        user_info=user_info
    )
    results.extend(service_results)
    
    await session.commit()
    
    text = "\n".join(results)
    if is_callback:
        await message.reply(text)
    else:
        await message.reply(text)
