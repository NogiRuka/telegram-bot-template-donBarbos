from aiogram import F, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy import select, func

from bot.database.database import sessionmaker
from bot.database.models.notification import NotificationModel
from bot.database.models.emby_item import EmbyItemModel
from bot.keyboards.inline.labels import (
    ADMIN_NEW_ITEM_NOTIFICATION_LABEL,
    NOTIFY_COMPLETE_LABEL,
    NOTIFY_PREVIEW_LABEL,
    NOTIFY_SEND_LABEL,
)
from bot.keyboards.inline.notification import get_notification_panel_keyboard
from bot.services.emby_service import fetch_and_save_item_details
from bot.services.main_message import MainMessageService
from bot.utils.images import get_common_image

router = Router(name="notification")


@router.callback_query(F.data == "admin:new_item_notification")
async def show_notification_panel(
    callback: types.CallbackQuery, 
    main_msg: MainMessageService
) -> None:
    """显示新片通知管理面板"""
    async with sessionmaker() as session:
        # 统计各状态数量
        pending_completion = await session.scalar(
            select(func.count(NotificationModel.id)).where(NotificationModel.status == "pending_completion")
        ) or 0
        pending_review = await session.scalar(
            select(func.count(NotificationModel.id)).where(NotificationModel.status == "pending_review")
        ) or 0

    text = (
        f"<b>{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}</b>\n\n"
        f"📊 <b>状态统计:</b>\n"
        f"• 待补全: <b>{pending_completion}</b>\n"
        f"• 待发送: <b>{pending_review}</b>\n\n"
        f"请选择操作:"
    )

    kb = get_notification_panel_keyboard(pending_completion, pending_review)

    await main_msg.update_on_callback(callback, text, kb, image_path=get_common_image())
    await callback.answer()


@router.callback_query(F.data == "notify:complete")
async def handle_notify_complete(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """执行上新补全"""
    # 移除旧的即时应答，改为在确认有任务后弹窗提示
    # await callback.answer("⏳ 正在后台补全元数据...", show_alert=False)
    
    success_count = 0
    fail_count = 0
    
    async with sessionmaker() as session:
        # 获取所有待补全的通知
        stmt = select(NotificationModel).where(NotificationModel.status == "pending_completion")
        result = await session.execute(stmt)
        notifications = result.scalars().all()
        
        if not notifications:
            await callback.answer("没有待补全的通知", show_alert=True)
            return

        total = len(notifications)
        # 提示改为 Alert 形式
        await callback.answer(f"⏳ 开始补全 {total} 条记录...", show_alert=True)

        # 提取 item_ids 并批量查询
        item_ids = list({n.item_id for n in notifications if n.item_id})
        
        # 批量调用 Service
        batch_results = await fetch_and_save_item_details(session, item_ids)

        for notif in notifications:
            if not notif.item_id:
                notif.status = "failed"
                fail_count += 1
                continue
                
            # 根据批量结果更新状态
            if batch_results.get(notif.item_id):
                notif.status = "pending_review"
                success_count += 1
            else:
                notif.status = "failed"
                fail_count += 1
        
        await session.commit()
        
        # 刷新界面显示结果
        pending_completion = await session.scalar(
            select(func.count(NotificationModel.id)).where(NotificationModel.status == "pending_completion")
        ) or 0
        pending_review = await session.scalar(
            select(func.count(NotificationModel.id)).where(NotificationModel.status == "pending_review")
        ) or 0

        text = (
            f"<b>{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}</b>\n\n"
            f"📊 <b>状态统计:</b>\n"
            f"• 待补全: <b>{pending_completion}</b>\n"
            f"• 待发送: <b>{pending_review}</b>\n\n"
            f"✅ <b>操作完成:</b> 成功 {success_count}, 失败 {fail_count}\n"
            f"请选择操作:"
        )

        kb = get_notification_panel_keyboard(pending_completion, pending_review)
        await main_msg.update_on_callback(callback, text, kb, image_path=get_common_image())
        
        # 刷新面板
        await show_notification_panel(callback, main_msg)


@router.callback_query(F.data == "notify:preview")
async def handle_notify_preview(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """预览待发送列表"""
    async with sessionmaker() as session:
        # 联查 Notification 和 EmbyItem
        stmt = (
            select(NotificationModel, EmbyItemModel)
            .join(EmbyItemModel, NotificationModel.item_id == EmbyItemModel.id)
            .where(NotificationModel.status == "pending_review")
            .limit(10) # 限制预览数量
        )
        result = await session.execute(stmt)
        rows = result.all()
        
    if not rows:
        await callback.answer("没有待发送的通知", show_alert=True)
        return

    text_lines = ["<b>👀 待发送预览 (前10条):</b>\n"]
    for notif, item in rows:
        text_lines.append(f"• {item.name} ({item.type})")
        
    text = "\n".join(text_lines)
    
    # 使用弹窗显示预览，或者发送一条临时消息
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "notify:send_all")
async def handle_notify_send_all(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """一键发送通知"""
    # 确认对话框
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 确认发送", callback_data="notify:confirm_send"),
            InlineKeyboardButton(text="❌ 取消", callback_data="admin:new_item_notification")
        ]
    ])
    await main_msg.update_on_callback(
        callback, 
        "⚠️ <b>确认操作</b>\n\n确定要将所有 [待发送] 状态的通知推送到频道/群组吗？", 
        confirm_kb
    )


@router.callback_query(F.data == "notify:confirm_send")
async def execute_send_all(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """执行批量发送"""
    await callback.answer("🚀 开始推送...", show_alert=False)
    
    sent_count = 0
    fail_count = 0
    
    async with sessionmaker() as session:
        stmt = (
            select(NotificationModel, EmbyItemModel)
            .join(EmbyItemModel, NotificationModel.item_id == EmbyItemModel.id)
            .where(NotificationModel.status == "pending_review")
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            await callback.answer("没有可发送的通知", show_alert=True)
            # 返回面板
            await show_notification_panel(callback, main_msg)
            return

        # TODO: 从配置读取目标频道/群组 ID
        # target_chat_id = settings.NOTIFICATION_CHANNEL_ID 
        # 这里暂时发给当前用户(管理员)作为演示
        target_chat_id = callback.from_user.id

        for notif, item in rows:
            try:
                # 构造消息内容
                overview = item.overview or "无简介"
                msg_text = (
                    f"📢 <b>新内容入库</b>\n\n"
                    f"🎬 <b>{item.name}</b> ({item.type})\n"
                    f"📅 {item.date_created[:10] if item.date_created else '未知'}\n"
                    f"📝 {overview[:150] + '...' if len(overview) > 150 else overview}\n\n"
                    f"#NewItem"
                )
                
                # 发送
                await callback.bot.send_message(chat_id=target_chat_id, text=msg_text)
                
                # 更新状态
                notif.status = "sent"
                notif.target_channel_id = str(target_chat_id)
                sent_count += 1
                
            except Exception as e:
                logger.error(f"❌ 发送通知失败: {item.name} -> {e}")
                notif.status = "failed"
                fail_count += 1
        
        await session.commit()
    
    await callback.answer(f"✅ 推送完成: 成功 {sent_count}, 失败 {fail_count}", show_alert=True)
    await show_notification_panel(callback, main_msg)
