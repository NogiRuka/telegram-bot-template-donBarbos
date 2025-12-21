import asyncio

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_PENDING_COMPLETION,
    NOTIFICATION_STATUS_PENDING_REVIEW,
    NOTIFICATION_STATUS_REJECTED,
    NOTIFICATION_STATUS_SENT,
)
from bot.database.models.emby_item import EmbyItemModel
from bot.database.models.notification import NotificationModel
from bot.keyboards.inline.admin import get_notification_panel_keyboard
from bot.keyboards.inline.buttons import (
    NOTIFY_CLOSE_PREVIEW_BUTTON,
    NOTIFY_CONFIRM_SEND_BUTTON,
    NOTIFY_CONFIRM_SEND_CANCEL_BUTTON,
)
from bot.keyboards.inline.constants import ADMIN_NEW_ITEM_NOTIFICATION_LABEL
from bot.services.emby_service import fetch_and_save_item_details
from bot.services.main_message import MainMessageService
from bot.utils.images import get_common_image
from bot.utils.message import delete_message, delete_message_after_delay
from bot.utils.notification import (
    get_check_id_for_notification,
    get_notification_content,
    get_notification_status_counts,
)

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
    pending_completion, pending_review, _ = await get_notification_status_counts(session)

    text = (
        f"<b>{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}</b>\n\n"
        f"📊 <b>状态统计:</b>\n"
        f"• 待补全：<b>{pending_completion}</b>\n"
        f"• 待发送：<b>{pending_review}</b>\n"
    )
    kb = get_notification_panel_keyboard(pending_completion, pending_review)

    await main_msg.update_on_callback(callback, text, kb, image_path=get_common_image())


@router.callback_query(F.data == "admin:notify_complete")
async def handle_notify_complete(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """执行上新补全（口径与统计完全一致）"""

    success_count = 0
    fail_count = 0

    # 1️⃣ 获取所有待补全的 library.new 通知（行级）
    stmt = select(NotificationModel).where(
        NotificationModel.status == NOTIFICATION_STATUS_PENDING_COMPLETION,
        NotificationModel.type == EVENT_TYPE_LIBRARY_NEW
    )
    result = await session.execute(stmt)
    notifications = result.scalars().all()

    if not notifications:
        await callback.answer("🈚 没有待补全的通知", show_alert=False)
        return

    # 2️⃣ 按统计规则分组（Episode → series_id，其它 → item_id）
    grouped: dict[int, list[NotificationModel]] = {}

    for notif in notifications:
        key = notif.series_id if notif.item_type == "Episode" and notif.series_id else notif.item_id
        if not key:
            notif.status = NOTIFICATION_STATUS_FAILED
            fail_count += 1
            continue
        grouped.setdefault(key, []).append(notif)

    # ✅ 真实补全数量（作品数）
    await callback.answer(
        f"⏳ 开始补全 {len(grouped)} 个作品...",
        show_alert=False
    )

    # 3️⃣ 只对唯一 key 做补全
    unique_keys = list(grouped.keys())
    batch_results = await fetch_and_save_item_details(
        session,
        unique_keys
    )

    # 4️⃣ 按 key 的补全结果，回写该组下所有通知状态
    for key, group in grouped.items():
        ok = batch_results.get(key, False)
        # ✅ key 级计数（只加一次）
        if ok:
            success_count += 1
        else:
            fail_count += 1

        # 行级只改状态，不计数
        for notif in group:
            notif.status = (
                NOTIFICATION_STATUS_PENDING_REVIEW
                if ok
                else NOTIFICATION_STATUS_FAILED
            )
    await session.commit()

    # 5️⃣ 刷新面板统计（这里依然是行级，和你原来一致）
    pending_completion, pending_review, _ = await get_notification_status_counts(session)
    text = (
        f"<b>{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}</b>\n\n"
        f"📊 <b>状态统计:</b>\n"
        f"• 待补全：<b>{pending_completion}</b>\n"
        f"• 待发送：<b>{pending_review}</b>\n\n"
        f"✅ <b>操作完成：</b> 成功 {success_count}, 失败 {fail_count}\n"
    )
    kb = get_notification_panel_keyboard(pending_completion, pending_review)
    await main_msg.update_on_callback(callback, text, kb, image_path=get_common_image())


@router.callback_query(F.data == "admin:notify_preview")
async def handle_notify_preview(
    callback: types.CallbackQuery,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """生成通知预览 - 每条消息关联具体通知ID"""
    preview_key = case(
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

    subq = (
        select(
            func.min(NotificationModel.id).label("notif_id"),
            preview_key.label("biz_id"),
        )
        .where(
            NotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
            NotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
        )
        .group_by(preview_key)
        .subquery()
    )

    stmt = (
        select(NotificationModel, EmbyItemModel)
        .join(subq, NotificationModel.id == subq.c.notif_id)
        .join(EmbyItemModel, EmbyItemModel.id == subq.c.biz_id)
    )

    rows = (await session.execute(stmt)).all()

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
    session: AsyncSession
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
    await delete_message(callback.message)

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

    await callback.answer(
        "请输入要添加的通知者信息（可以是用户ID、用户名等）：\n"
        "或者直接回复消息来引用用户"
    )


@router.callback_query(F.data == "admin:notify_close_preview")
async def handle_close_preview(callback: types.CallbackQuery, state: FSMContext) -> None:
    """关闭所有预览消息"""
    user_id = callback.from_user.id

    # 从FSM状态获取预览数据
    data = await state.get_data()
    preview_data = data.get("preview_data", {})

    if preview_data:
        # 删除所有预览消息
        for msg_id in preview_data:
            try:
                await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except Exception:
                pass # 忽略已删除或不存在的消息

        # 清除预览数据
        await state.update_data(preview_data={})
    else:
        # 可能是缓存过期或重启，尝试删除当前这一条
        await delete_message(callback.message)
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

    # 删除用户输入的消息，保持对话框清洁
    await delete_message(message)

    # 解析用户输入（可以是用户ID、用户名等）
    if not message.text:
        await message.answer("❌ 请输入有效的通知者信息")
        await state.clear()
        return

    sender_info = message.text.strip()

    # 获取当前的发送者信息
    current_senders = notification.target_channel_id or ""

    # 添加新的通知者
    new_senders = f"{current_senders},{sender_info}" if current_senders else sender_info

    notification.target_channel_id = new_senders
    if message.from_user:
        notification.updated_by = message.from_user.id

    await session.commit()

    # 发送成功消息
    success_msg = await message.answer(
        f"✅ 已为通知 '{notification.item_name or notification.series_name or '未知'}' "
        f"添加通知者: {sender_info}"
    )

    # 3秒后删除成功消息
    delete_message_after_delay(success_msg)

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

            # 合并目标频道：配置的频道 + 通知原有的target_channel_id
            all_target_chat_ids = list(target_chat_ids)  # 从配置获取的频道

            # 如果通知本身有target_channel_id，也要发送给这些人
            if notif.target_channel_id:
                try:
                    # 解析原有的target_channel_id（逗号分隔的字符串）
                    existing_targets = [int(x.strip()) for x in notif.target_channel_id.split(",") if x.strip()]
                    # 添加到目标列表中，避免重复
                    for target in existing_targets:
                        if target not in all_target_chat_ids:
                            all_target_chat_ids.append(target)
                except ValueError as e:
                    logger.warning(f"⚠️ 解析通知的target_channel_id失败: {notif.target_channel_id} -> {e}")

            # 发送给所有目标频道（配置频道 + 原有目标）
            send_success = False
            for chat_id in all_target_chat_ids:
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
                # 记录发送的目标ID列表（包含配置频道和原有目标）
                notif.target_channel_id = ",".join(str(x) for x in all_target_chat_ids)
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

    pending_completion, pending_review, _ = await get_notification_status_counts(session)
    text = (
        f"<b>{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}</b>\n\n"
        f"📊 <b>状态统计:</b>\n"
        f"• 待补全：<b>{pending_completion}</b>\n"
        f"• 待发送：<b>{pending_review}</b>\n\n"
        f"✅ <b>操作完成：</b> 成功 {sent_count}, 失败 {fail_count}\n"
    )
    kb = get_notification_panel_keyboard(pending_completion, pending_review)
    await main_msg.update_on_callback(callback, text, kb, image_path=get_common_image())
