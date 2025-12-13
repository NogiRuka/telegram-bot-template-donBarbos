from aiogram import F, Router, types
from aiogram.exceptions import TelegramBadRequest
from loguru import logger
from sqlalchemy import select

from bot.database.database import sessionmaker
from bot.database.models.notification import NotificationModel
from bot.services.emby_service import get_item_details
from bot.services.main_message import MainMessageService

router = Router(name="notification")

@router.callback_query(F.data.startswith("notify_approve:"))
async def handle_notify_approve(
    callback: types.CallbackQuery, 
    main_msg: MainMessageService
) -> None:
    """处理通知批准"""
    try:
        notification_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ 无效的参数", show_alert=True)
        return
    
    async with sessionmaker() as session:
        # 获取通知记录
        stmt = select(NotificationModel).where(NotificationModel.id == notification_id)
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if not notification:
            await callback.answer("❌ 通知记录不存在", show_alert=True)
            return
            
        if notification.status != "pending":
            await callback.answer(f"⚠️ 该通知状态为 {notification.status}，无法操作", show_alert=True)
            return

        # 更新状态为 approved
        notification.status = "approved"
        await session.commit()
        
        await callback.answer("✅ 已批准，正在获取最新元数据...")
        
        # 获取 Emby 详情
        try:
            # 这里的 get_item_details 已经包含了我们修改过的 get_items 逻辑
            details = await get_item_details(notification.item_id)
            
            if not details:
                # 尝试编辑消息，如果消息太旧可能会失败
                caption = f"{callback.message.html_text}\n\n❌ <b>发送失败:</b> 无法从 Emby 获取项目详情 (ID: {notification.item_id})"
                await main_msg.update_on_callback(callback, caption, None)
                
                notification.status = "failed"
                await session.commit()
                return

            # 构建最终通知消息
            name = details.get("Name", notification.item_name)
            overview = details.get("Overview", "无简介")
            
            # 简单的消息格式，后续可根据需求美化
            msg_text = (
                f"📢 <b>新内容入库</b>\n\n"
                f"🎬 <b>{name}</b>\n"
                f"📝 {overview[:200] + '...' if len(overview) > 200 else overview}\n\n"
                f"#NewItem"
            )
            
            # 发送通知 (此处演示发回给管理员，实际应发给频道)
            # TODO: 读取配置中的 Channel ID 进行发送
            sent_msg = await callback.message.answer(msg_text)
            
            notification.status = "sent"
            await session.commit()
            
            # 更新原管理消息
            caption = f"{callback.message.html_text}\n\n✅ <b>已发送通知</b>"
            await main_msg.update_on_callback(callback, caption, None)
            
        except Exception as e:
            logger.exception("处理通知批准时发生错误")
            await callback.message.answer(f"❌ 处理出错: {e}")
            notification.status = "failed"
            await session.commit()

@router.callback_query(F.data.startswith("notify_reject:"))
async def handle_notify_reject(
    callback: types.CallbackQuery, 
    main_msg: MainMessageService
) -> None:
    """处理通知拒绝"""
    try:
        notification_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ 无效的参数", show_alert=True)
        return
    
    async with sessionmaker() as session:
        stmt = select(NotificationModel).where(NotificationModel.id == notification_id)
        result = await session.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if not notification:
            await callback.answer("❌ 通知记录不存在", show_alert=True)
            return
            
        notification.status = "rejected"
        await session.commit()
        
        caption = f"{callback.message.html_text}\n\n🚫 <b>已拒绝/忽略</b>"
        await main_msg.update_on_callback(callback, caption, None)
            
        await callback.answer("已忽略")
