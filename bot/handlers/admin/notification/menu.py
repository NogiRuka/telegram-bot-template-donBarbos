from aiogram import F, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_PENDING_COMPLETION,
    NOTIFICATION_STATUS_PENDING_REVIEW,
)
from bot.database.models.library_new_notification import LibraryNewNotificationModel
from bot.database.models.notification import NotificationModel
from bot.database.models.user_submission import UserSubmissionModel
from bot.keyboards.inline.admin import get_notification_panel_keyboard
from bot.keyboards.inline.constants import ADMIN_NEW_ITEM_NOTIFICATION_LABEL
from bot.services.emby_service import fetch_and_save_item_details
from bot.services.main_message import MainMessageService
from bot.utils.notification import get_notification_status_counts
from bot.utils.message import clear_message_list_from_state

from .router import router

@router.callback_query(F.data == "admin:new_item_notification")
async def show_notification_panel(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
    state: FSMContext,
) -> None:
    """显示新片通知管理面板"""
    await clear_message_list_from_state(state, callback.bot, callback.message.chat.id, "preview_data")
    await clear_message_list_from_state(state, callback.bot, callback.message.chat.id, "submission_review_ids")

    pending_completion, pending_review, _ = await get_notification_status_counts(session)

    # 计算待审核投稿数量
    submission_count_stmt = select(func.count()).select_from(UserSubmissionModel).where(
        UserSubmissionModel.status == "pending"
    )
    pending_submissions = (await session.execute(submission_count_stmt)).scalar_one()

    text = (
        f"*{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}*\n\n"
        f"📊 *状态统计:*\n"
        f"• 待补全：*{pending_completion}*\n"
        f"• 待发送：*{pending_review}*\n"
        f"• 待审核投稿：*{pending_submissions}*\n"
    )
    kb = get_notification_panel_keyboard(pending_completion, pending_review, pending_submissions)

    await main_msg.update_on_callback(callback, text, kb)


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
    stmt = select(LibraryNewNotificationModel).where(
        LibraryNewNotificationModel.status == NOTIFICATION_STATUS_PENDING_COMPLETION,
        LibraryNewNotificationModel.type == EVENT_TYPE_LIBRARY_NEW
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
        f"*{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}*\n\n"
        f"📊 *状态统计:*\n"
        f"• 待补全：*{pending_completion}*\n"
        f"• 待发送：*{pending_review}*\n\n"
        f"✅ *操作完成：* 成功 {success_count}, 失败 {fail_count}\n"
    )
    kb = get_notification_panel_keyboard(pending_completion, pending_review)
    await main_msg.update_on_callback(callback, text, kb)


@router.callback_query(F.data == "admin:notify_preview_to_complete")
async def handle_notify_preview_to_complete(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """将预览状态的通知变成补全状态"""
    
    # 获取所有预览状态的通知
    stmt = select(LibraryNewNotificationModel).where(
        LibraryNewNotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
        LibraryNewNotificationModel.type == EVENT_TYPE_LIBRARY_NEW
    )
    result = await session.execute(stmt)
    notifications = result.scalars().all()
    
    if not notifications:
        await callback.answer("🈚 没有预览状态的通知", show_alert=False)
        return
    
    # 将所有预览状态的通知改为补全状态
    for notification in notifications:
        notification.status = NOTIFICATION_STATUS_PENDING_COMPLETION
    
    await session.commit()
    
    # 刷新面板统计
    pending_completion, pending_review, _ = await get_notification_status_counts(session)
    text = (
        f"*{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}*\n\n"
        f"📊 *状态统计:*\n"
        f"• 待补全：*{pending_completion}*\n"
        f"• 待发送：*{pending_review}*\n\n"
        f"✅ *操作完成：* 已将 {len(notifications)} 个预览状态通知转为补全状态\n"
    )
    kb = get_notification_panel_keyboard(pending_completion, pending_review)
    await main_msg.update_on_callback(callback, text, kb)
