from aiogram import F, Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy import select, func

from bot.core.config import settings
from bot.database.database import sessionmaker
from bot.database.models.notification import NotificationModel
from bot.database.models.emby_item import EmbyItemModel
from bot.keyboards.inline.constants import (
    ADMIN_NEW_ITEM_NOTIFICATION_LABEL
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


def get_notification_content(item: EmbyItemModel) -> tuple[str, str | None]:
    """生成通知消息内容和图片URL"""
    # 构造图片 URL
    image_url = None
    if item.image_tags and "Primary" in item.image_tags:
        tag = item.image_tags["Primary"]
        base_url = settings.get_emby_base_url()
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        image_url = f"{base_url}/Items/{item.id}/Images/Primary?tag={tag}"

    # 解析媒体库名称 (Library Tag)
    library_tag = ""
    if item.path:
        path = item.path.replace("\\", "/")
        parts = [p for p in path.split("/") if p]
        
        if "钙片" in parts:
            idx = parts.index("钙片")
            if idx + 1 < len(parts):
                library_tag = f"#{parts[idx+1]}"
        elif "剧集" in parts:
             library_tag = "#剧集"
        elif "电影" in parts:
             library_tag = "#电影"

    # 构造消息内容
    overview = item.overview or "无简介"
    
    # 处理剧集信息（仅Series类型显示）
    series_info = ""
    if item.item_type == "Series":
        # 进度信息
        if item.current_season and item.current_episode:
            series_info += f"📺 <b>进度：</b>第{item.current_season}季第{item.current_episode}集\n"
        
        # 状态信息
        if item.status:
            status_text = item.status
            if item.status == "Continuing":
                status_text = "连载中"
            elif item.status == "Ended":
                status_text = "已完结"
            series_info += f"📊 <b>状态：</b>{status_text}\n"
    
    # 用户指定的简洁格式
    msg_text = (
        f"🎬 <b>名称：</b><code>{item.name}</code>\n"
        f"{series_info}"
        f"📂 <b>分类：</b>{library_tag}\n"
        f"📅 <b>时间：</b>{item.date_created if item.date_created else '未知'}\n"
        f"📝 <b>简介：</b>{overview[:80] + '...' if len(overview) > 80 else overview}"
    )
    
    return msg_text, image_url


@router.callback_query(F.data == "notify:complete")
async def handle_notify_complete(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """执行上新补全"""
    
    success_count = 0
    fail_count = 0
    
    async with sessionmaker() as session:
        # 获取所有待补全的library.new通知
        stmt = select(NotificationModel).where(
            NotificationModel.status == "pending_completion",
            NotificationModel.type == "library.new"
        )
        result = await session.execute(stmt)
        notifications = result.scalars().all()
        
        if not notifications:
            await callback.answer("🈚 没有待补全的通知", show_alert=False)
            return

        total = len(notifications)
        # 提示改为 Alert 形式，不需要用户确认
        await callback.answer(f"⏳ 开始补全 {total} 条记录...", show_alert=False)

        # 简化逻辑：提取需要去查询的item_ids
        # 对于Episode类型，使用series_id；对于其他类型，使用item_id
        item_ids_to_query = []
        for notif in notifications:
            if notif.item_id:
                if notif.item_type == "Episode" and notif.series_id:
                    # Episode类型使用series_id
                    item_ids_to_query.append(notif.series_id)
                else:
                    # 其他类型使用item_id
                    item_ids_to_query.append(notif.item_id)
        
        # 去重
        unique_item_ids = list(set(item_ids_to_query))
        
        # 批量调用 Service
        batch_results = await fetch_and_save_item_details(session, unique_item_ids)

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
        # await show_notification_panel(callback, main_msg)


@router.callback_query(F.data == "notify:preview")
async def handle_notify_preview(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """预览待发送列表"""
    async with sessionmaker() as session:
        # 联查 Notification 和 EmbyItem
        # 对于Episode类型，使用series_id关联；其他类型使用item_id关联
        stmt = (
            select(NotificationModel, EmbyItemModel)
            .join(
                EmbyItemModel, 
                (NotificationModel.item_id == EmbyItemModel.id) |
                ((NotificationModel.item_type == "Episode") & 
                 (NotificationModel.series_id == EmbyItemModel.id)),
                isouter=True
            )
            .where(NotificationModel.status == "pending_review")
            # .limit(10) # 预览所有，暂不限制
        )
        result = await session.execute(stmt)
        rows = result.all()
        
    if not rows:
        await callback.answer("没有待发送的通知", show_alert=True)
        return

    # 发送提示
    await callback.answer(f"👀 正在生成 {len(rows)} 条预览...", show_alert=False)

    preview_msg_ids = []
    
    for notif, item in rows:
        msg_text, image_url = get_notification_content(item)
        
        # 发送
        try:
            if image_url:
                msg = await callback.bot.send_photo(chat_id=callback.from_user.id, photo=image_url, caption=msg_text)
            else:
                msg = await callback.bot.send_message(chat_id=callback.from_user.id, text=msg_text)
            
            preview_msg_ids.append(msg.message_id)
        except Exception as e:
            logger.error(f"预览发送失败: {e}")

    # 存储: PREVIEW_CACHE[user_id] = [msg_id1, msg_id2, ...]
    global PREVIEW_CACHE
    if 'PREVIEW_CACHE' not in globals():
        PREVIEW_CACHE = {}
    
    PREVIEW_CACHE[callback.from_user.id] = preview_msg_ids
    
    # 构造统一的关闭按钮
    close_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ 关闭预览 (删除所有)", callback_data="notify:close_preview")]
    ])

    # 更新所有发送出的消息，加上键盘
    for msg_id in preview_msg_ids:
        try:
            # 注意: edit_message_reply_markup 需要 chat_id 和 message_id
            await callback.bot.edit_message_reply_markup(
                chat_id=callback.from_user.id,
                message_id=msg_id,
                reply_markup=close_kb
            )
        except Exception as e:
            logger.warning(f"无法为预览消息添加关闭按钮: {msg_id} -> {e}")

    await callback.answer()


@router.callback_query(F.data == "notify:close_preview")
async def handle_close_preview(callback: types.CallbackQuery):
    """关闭所有预览消息"""
    user_id = callback.from_user.id
    global PREVIEW_CACHE
    if 'PREVIEW_CACHE' in globals() and user_id in PREVIEW_CACHE:
        msg_ids = PREVIEW_CACHE[user_id]
        for mid in msg_ids:
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=mid)
            except Exception:
                pass # 忽略已删除或不存在的消息
        del PREVIEW_CACHE[user_id]
        # await callback.answer("已清除预览", show_alert=False)
    else:
        # 可能是缓存过期或重启，尝试删除当前这一条
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.answer("预览缓存已失效，仅删除当前消息", show_alert=False)


@router.callback_query(F.data == "notify:send_all")
async def handle_notify_send_all(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """一键发送通知"""
    
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
            .join(
                EmbyItemModel, 
                (NotificationModel.item_id == EmbyItemModel.id) |
                ((NotificationModel.item_type == "Episode") & 
                 (NotificationModel.series_id == EmbyItemModel.id)),
                isouter=True
            )
            .where(NotificationModel.status == "pending_review")
        )
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            await callback.answer("没有可发送的通知", show_alert=True)
            # 返回面板
            await show_notification_panel(callback, main_msg)
            return

        # 获取目标频道ID列表
        target_chat_ids = settings.get_notification_channel_ids()
        
        # 如果未配置，回退到发送给当前管理员
        if not target_chat_ids:
            target_chat_ids = [callback.from_user.id]
            logger.warning("未配置 NOTIFICATION_CHANNEL_ID，将通知发送给当前管理员")

        for notif, item in rows:
            try:
                msg_text, image_url = get_notification_content(item)
                
                # 发送给所有目标频道
                send_success = False
                for chat_id in target_chat_ids:
                    try:
                        if image_url:
                            await callback.bot.send_photo(chat_id=chat_id, photo=image_url, caption=msg_text)
                        else:
                            await callback.bot.send_message(chat_id=chat_id, text=msg_text)
                        send_success = True
                    except Exception as e:
                        logger.error(f"❌ 发送通知到 {chat_id} 失败: {item.name} -> {e}")
                
                # 只要有一个发送成功，就标记为成功
                if send_success:
                    notif.status = "sent"
                    # 记录发送的目标ID列表
                    notif.target_channel_id = ",".join(str(x) for x in target_chat_ids)
                    sent_count += 1
                else:
                    notif.status = "failed"
                    fail_count += 1
                
            except Exception as e:
                logger.error(f"❌ 处理通知失败: {item.name} -> {e}")
                notif.status = "failed"
                fail_count += 1
        
        await session.commit()
    
    await callback.answer(f"✅ 推送完成: 成功 {sent_count}, 失败 {fail_count}", show_alert=True)
    await show_notification_panel(callback, main_msg)
