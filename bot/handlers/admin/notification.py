from aiogram import F, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    NOTIFICATION_STATUS_PENDING_COMPLETION,
    NOTIFICATION_STATUS_PENDING_REVIEW,
    NOTIFICATION_STATUS_SENT,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_REJECTED
)
from bot.database.models.notification import NotificationModel
from bot.database.models.emby_item import EmbyItemModel
from bot.keyboards.inline.constants import (
    ADMIN_NEW_ITEM_NOTIFICATION_LABEL
)
from bot.keyboards.inline.buttons import (
    NOTIFY_CONFIRM_SEND_BUTTON,
    NOTIFY_CONFIRM_SEND_CANCEL_BUTTON
)
from bot.keyboards.inline.buttons import NOTIFY_CLOSE_PREVIEW_BUTTON
from bot.keyboards.inline.admin import get_notification_panel_keyboard
from bot.services.emby_service import fetch_and_save_item_details
from bot.services.main_message import MainMessageService
from bot.utils.images import get_common_image

router = Router(name="notification")


class NotificationStates(StatesGroup):
    """通知相关状态"""
    waiting_for_additional_sender = State()  # 等待输入额外通知者


@router.callback_query(F.data == "admin:new_item_notification")
async def show_notification_panel(
    callback: types.CallbackQuery, 
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """显示新片通知管理面板"""
    count_key = case(
        (
            (NotificationModel.item_type == "Episode")
            & (NotificationModel.series_id.isnot(None)),
            NotificationModel.series_id,
        ),
        (
            NotificationModel.item_type == "Series",
            NotificationModel.item_id,
        ),
        else_=NotificationModel.item_id,
    )
    stmt = (
        select(
            NotificationModel.status,
            func.count(func.distinct(count_key)).label("cnt"),
        )
        .where(
            NotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
            NotificationModel.status.in_(
                [NOTIFICATION_STATUS_PENDING_COMPLETION, NOTIFICATION_STATUS_PENDING_REVIEW, "rejected"]
            ),
        )
        .group_by(NotificationModel.status)
    )
    rows = await session.execute(stmt)
    counts = {row.status: row.cnt for row in rows}

    pending_completion = counts.get(NOTIFICATION_STATUS_PENDING_COMPLETION, 0)
    pending_review = counts.get(NOTIFICATION_STATUS_PENDING_REVIEW, 0)
    rejected = counts.get("rejected", 0)

    text = (
        f"<b>{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}</b>\n\n"
        f"📊 <b>状态统计:</b>\n"
        f"• 待补全: <b>{pending_completion}</b>\n"
        f"• 待发送: <b>{pending_review}</b>\n"
        f"• 已拒绝: <b>{rejected}</b>\n\n"
        f"请选择操作:"
    )

    kb = get_notification_panel_keyboard(pending_completion, pending_review)
    await main_msg.update_on_callback(callback, text, kb, image_path=get_common_image())


def get_check_id_for_notification(notif: NotificationModel) -> str:
    """根据通知类型获取用于检测的ID
    
    对于Episode类型使用series_id，其他类型使用item_id
    """
    if notif.item_type == "Episode" and notif.series_id:
        return notif.series_id
    return notif.item_id


def get_item_ids_from_notifications(notifications: list[NotificationModel]) -> list[str]:
    """从通知列表中提取需要去查询的item_id列表
    
    对于Episode类型使用series_id，其他类型使用item_id，并去重
    """
    item_ids = []
    for notif in notifications:
        check_id = get_check_id_for_notification(notif)
        if check_id:
            item_ids.append(check_id)
    
    # 去重
    return list(set(item_ids))


def get_notification_content(item: EmbyItemModel) -> tuple[str, str | None]:
    """生成通知消息内容和图片URL"""
    # 构造图片 URL
    image_url = None
    if item.image_tags:
        # 优先使用Primary标签，如果没有则使用Logo标签
        tag = None
        image_type = None
        if "Primary" in item.image_tags:
            tag = item.image_tags["Primary"]
            image_type = "Primary"
        elif "Logo" in item.image_tags:
            tag = item.image_tags["Logo"]
            image_type = "Logo"
        
        if tag and image_type:
            base_url = settings.get_emby_base_url()
            if base_url.endswith("/"):
                base_url = base_url[:-1]
            image_url = f"{base_url}/Items/{item.id}/Images/{image_type}?tag={tag}"

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
    overview = item.overview or ""
    
    # 处理剧集信息（仅Series类型显示）
    series_info = ""
    if item.type == "Series":
        # 进度信息
        if item.current_season and item.current_episode:
            series_info += f"📺 <b>进度：</b>第{item.current_season}季 · 第{item.current_episode}集\n"
        
        # 状态信息
        if item.status:
            status_text = item.status
            if item.status == "Continuing":
                status_text = "更新中"
            elif item.status == "Ended":
                status_text = "已完结"
            series_info += f"📊 <b>状态：</b>{status_text}\n"
    
    # 用户指定的简洁格式 - 只在有内容时显示对应字段
    msg_parts = [f"🎬 <b>名称：</b><code>{item.name}</code>"]
    
    # 分类信息（只在有分类时显示）
    if library_tag:
        msg_parts.append(f"📂 <b>分类：</b>{library_tag}")
    
    # 剧集信息
    if series_info:
        msg_parts.append(series_info.rstrip())
    
    # 时间信息
    msg_parts.append(f"📅 <b>时间：</b>{item.date_created if item.date_created else '未知'}")
    
    # 简介信息（只在有简介时显示）
    if overview:
        overview_text = overview[:150] + '...' if len(overview) > 150 else overview
        msg_parts.append(f"📝 <b>简介：</b>{overview_text}")
    
    msg_text = "\n".join(msg_parts)
    
    return msg_text, image_url


@router.callback_query(F.data == "admin:notify_complete")
async def handle_notify_complete(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """执行上新补全"""
    
    success_count = 0
    fail_count = 0
    
    # 获取所有待补全的library.new通知
    stmt = select(NotificationModel).where(
        NotificationModel.status == NOTIFICATION_STATUS_PENDING_COMPLETION,
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

    # 提取需要去查询的item_ids（使用公共函数）
    unique_item_ids = get_item_ids_from_notifications(notifications)
    
    # 批量调用 Service
    batch_results = await fetch_and_save_item_details(session, unique_item_ids)

    for notif in notifications:
        if not notif.item_id:
            notif.status = NOTIFICATION_STATUS_FAILED
            fail_count += 1
            continue
            
        # 根据批量结果更新状态
        # Episode类型使用series_id检测，其他类型使用item_id
        check_id = notif.item_id
        if notif.item_type == "Episode" and notif.series_id:
            check_id = notif.series_id
            
        if batch_results.get(check_id):
            notif.status = NOTIFICATION_STATUS_PENDING_REVIEW
            success_count += 1
        else:
            notif.status = NOTIFICATION_STATUS_FAILED
            fail_count += 1
    
    await session.commit()
    
    # 刷新界面显示结果
    pending_completion = await session.scalar(
        select(func.count(NotificationModel.id)).where(
            NotificationModel.status == NOTIFICATION_STATUS_PENDING_COMPLETION,
            NotificationModel.type == EVENT_TYPE_LIBRARY_NEW
        )
    ) or 0
    pending_review = await session.scalar(
        select(func.count(NotificationModel.id)).where(
            NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
            NotificationModel.type == EVENT_TYPE_LIBRARY_NEW
        )
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


@router.callback_query(F.data == "admin:notify_preview")
async def handle_notify_preview(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
    state: FSMContext
) -> None:
    """生成通知预览 - 每条消息关联具体通知ID"""

    preview_key = case(
        (
            (NotificationModel.item_type == "Episode")
            & (NotificationModel.series_id.isnot(None)),
            NotificationModel.series_id,
        ),
        else_=NotificationModel.item_id,
    )

    # 获取待审核的通知和对应的EmbyItem
    stmt = (
        select(NotificationModel, EmbyItemModel)
        .join(EmbyItemModel, preview_key == EmbyItemModel.id)
        .where(
            NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
            NotificationModel.type == EVENT_TYPE_LIBRARY_NEW
        )
        .distinct(preview_key)
    )

    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        await callback.answer("🈚 没有可预览的通知")
        return

    await callback.answer(f"👀 正在生成 {len(rows)} 条预览…")

    # 存储预览消息信息：{message_id: notification_id}
    preview_data = {}

    for notif, item in rows:
        msg_text, image_url = get_notification_content(item)
        
        # 创建操作键盘
        reject_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🚫 拒绝此通知", callback_data=f"admin:notify_reject:{notif.id}"),
                    InlineKeyboardButton(text="👥 添加通知者", callback_data=f"admin:notify_add_sender:{notif.id}")
                ],
                [NOTIFY_CLOSE_PREVIEW_BUTTON]
            ]
        )
        
        try:
            if image_url:
                msg = await callback.bot.send_photo(
                    callback.from_user.id,
                    photo=image_url,
                    caption=msg_text,
                    reply_markup=reject_kb,
                )
            else:
                msg = await callback.bot.send_message(
                    callback.from_user.id,
                    msg_text,
                    reply_markup=reject_kb,
                )
            
            # 关联消息ID和通知ID
            preview_data[msg.message_id] = notif.id
            
        except Exception as e:
            logger.error(f"预览发送失败: {e}")

    # 存储预览数据到FSM状态
    await state.update_data(preview_data=preview_data)


@router.callback_query(F.data.startswith("admin:notify_reject:"))
async def handle_notify_reject(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """拒绝单条通知 - 将指定通知状态改为rejected"""
    
    # 从callback_data中提取通知ID
    notification_id = int(callback.data.split(":")[2])
    
    # 获取指定通知
    stmt = select(NotificationModel).where(
        NotificationModel.id == notification_id,
        NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW
    )
    result = await session.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        await callback.answer("🈚 该通知不存在或状态已改变", show_alert=True)
        return
    
    # 拒绝该通知
    notification.status = NOTIFICATION_STATUS_REJECTED
    notification.updated_by = callback.from_user.id
    
    await session.commit()
    
    # 删除预览消息
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    await callback.answer(f"🚫 已拒绝通知: {notification.title or '未知'}")


@router.callback_query(F.data.startswith("admin:notify_add_sender:"))
async def handle_add_sender_start(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """开始添加通知者流程"""
    
    # 从callback_data中提取通知ID
    notification_id = int(callback.data.split(":")[2])
    
    # 存储通知ID到状态
    await state.update_data(notification_id=notification_id)
    await state.set_state(NotificationStates.waiting_for_additional_sender)
    
    await callback.message.answer(
        "请输入要添加的通知者信息（可以是用户ID、用户名等）：\n"
        "或者直接回复消息来引用用户"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:notify_close_preview")
async def handle_close_preview(callback: types.CallbackQuery, state: FSMContext):
    """关闭所有预览消息"""
    user_id = callback.from_user.id
    
    # 从FSM状态获取预览数据
    data = await state.get_data()
    preview_data = data.get("preview_data", {})
    
    if preview_data:
        # 删除所有预览消息
        for msg_id in preview_data.keys():
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass # 忽略已删除或不存在的消息
        
        # 清除预览数据
        await state.update_data(preview_data={})
    else:
        # 可能是缓存过期或重启，尝试删除当前这一条
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.answer("预览缓存已失效，仅删除当前消息", show_alert=False)


@router.message(NotificationStates.waiting_for_additional_sender)
async def handle_add_sender_complete(
    message: types.Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """处理添加通知者的输入"""
    
    data = await state.get_data()
    notification_id = data.get("notification_id")
    
    if not notification_id:
        await message.answer("❌ 状态错误，请重新操作")
        await state.clear()
        return
    
    # 获取通知
    stmt = select(NotificationModel).where(NotificationModel.id == notification_id)
    result = await session.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        await message.answer("❌ 通知不存在")
        await state.clear()
        return
    
    # 解析用户输入（可以是用户ID、用户名等）
    sender_info = message.text.strip()
    
    # 获取当前的发送者信息
    current_senders = notification.target_channel_id or ""
    
    # 添加新的通知者
    if current_senders:
        new_senders = f"{current_senders},{sender_info}"
    else:
        new_senders = sender_info
    
    notification.target_channel_id = new_senders
    notification.updated_by = message.from_user.id
    
    await session.commit()
    
    await message.answer(
        f"✅ 已为通知 '{notification.item_name or notification.series_name or '未知'}' "
        f"添加通知者: {sender_info}"
    )
    
    await state.clear()


@router.callback_query(F.data == "admin:notify_send")
async def handle_notify_send_all(
    callback: types.CallbackQuery,
    main_msg: MainMessageService
) -> None:
    """一键发送通知"""
    
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            NOTIFY_CONFIRM_SEND_BUTTON,
            NOTIFY_CONFIRM_SEND_CANCEL_BUTTON
        ]
    ])
    await main_msg.update_on_callback(
        callback, 
        "⚠️ <b>确认操作</b>\n\n确定要将所有 [待发送] 状态的通知推送到频道/群组吗？", 
        confirm_kb
    )


@router.callback_query(F.data == "admin:notify_confirm_send")
async def execute_send_all(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """执行批量发送"""
    await callback.answer("🚀 正在推送，请稍候...")
    
    sent_count = 0
    fail_count = 0
    
    # 获取所有待发送的通知
    stmt = select(NotificationModel).where(
        NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
        NotificationModel.type == EVENT_TYPE_LIBRARY_NEW
    )
    result = await session.execute(stmt)
    notifications = result.scalars().all()
    
    if not notifications:
        await callback.answer("🈚 没有可发送的通知", show_alert=True)
        # 返回面板
        await show_notification_panel(callback, session, main_msg)
        return

    # 获取目标频道ID列表
    target_chat_ids = settings.get_notification_channel_ids()
    
    # 如果未配置，回退到发送给当前管理员
    if not target_chat_ids:
        target_chat_ids = [callback.from_user.id]
        logger.warning("⚠️ 未配置 NOTIFICATION_CHANNEL_ID，将通知发送给当前管理员")

    # 按检测ID分组处理，避免同一剧集多集重复发送
    processed_items = set()
    
    for notif in notifications:
        try:
            # 获取用于检测的ID（Episode类型使用series_id）
            check_id = get_check_id_for_notification(notif)
            
            # 如果已经处理过这个item，跳过（避免多集重复）
            if check_id in processed_items:
                # 标记为已发送（因为是同一剧集的其他集数）
                notif.status = NOTIFICATION_STATUS_SENT
                notif.target_channel_id = ",".join(str(x) for x in target_chat_ids)
                sent_count += 1
                continue
                
            processed_items.add(check_id)
            
            # 获取对应的EmbyItem数据（使用原始item_id查询）
            item_stmt = select(EmbyItemModel).where(EmbyItemModel.id == check_id)
            item_result = await session.execute(item_stmt)
            item = item_result.scalar_one_or_none()
            
            if not item:
                logger.warning(f"⚠️ 未找到对应的EmbyItem: {check_id}")
                notif.status = NOTIFICATION_STATUS_FAILED
                fail_count += 1
                continue
            
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
                notif.status = NOTIFICATION_STATUS_SENT
                # 记录发送的目标ID列表
                notif.target_channel_id = ",".join(str(x) for x in target_chat_ids)
                # 记录发送者信息
                notif.updated_by = callback.from_user.id
                sent_count += 1
            else:
                notif.status = NOTIFICATION_STATUS_FAILED
                fail_count += 1
            
        except Exception as e:
            logger.error(f"❌ 处理通知失败: {notif.item_id} -> {e}")
            notif.status = NOTIFICATION_STATUS_FAILED
            fail_count += 1
    
    await session.commit()
    
    result_text = (
        f"✅ <b>推送完成</b>\n\n"
        f"📤 成功：<b>{sent_count}</b>\n"
        f"❌ 失败：<b>{fail_count}</b>"
    )

    await main_msg.update_on_callback(
        callback,
        result_text,
        get_notification_panel_keyboard(
            pending_completion=0,
            pending_review=0,
        ),
        image_path=get_common_image(),
    )