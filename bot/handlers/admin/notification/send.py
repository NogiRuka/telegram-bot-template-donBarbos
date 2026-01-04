from aiogram import F, types
from aiogram.types import InlineKeyboardMarkup
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_NOTIFICATION_CHANNELS
from bot.core.config import settings
from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    NOTIFICATION_STATUS_FAILED,
    NOTIFICATION_STATUS_PENDING_REVIEW,
    NOTIFICATION_STATUS_SENT,
)
from bot.database.models.emby_item import EmbyItemModel
from bot.database.models.library_new_notification import LibraryNewNotificationModel
from bot.database.models.user_submission import UserSubmissionModel
from bot.keyboards.inline.admin import get_notification_panel_keyboard
from bot.keyboards.inline.buttons import (
    NOTIFY_CONFIRM_SEND_BUTTON,
    NOTIFY_CONFIRM_SEND_CANCEL_BUTTON,
)
from bot.keyboards.inline.constants import ADMIN_NEW_ITEM_NOTIFICATION_LABEL
from bot.core.constants import CURRENCY_SYMBOL
from bot.services.config_service import get_config
from bot.services.main_message import MainMessageService
from bot.utils.notification import (
    get_check_id_for_notification,
    get_notification_content,
    get_notification_status_counts,
)

from .router import router
from .menu import show_notification_panel


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
        "⚠️ *确认操作*\n\n确定要将所有 \\[待发送\\] 状态的通知推送到频道/群组吗？",
        confirm_kb
    )


@router.callback_query(F.data == "admin:notify_confirm_send")
async def execute_send_all(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """执行批量发送
    
    功能说明:
    - 将所有待发送的通知推送到配置的频道/群组
    - 如果存在 LibraryNewNotificationModel.target_user__id，则对这些用户发送差异化通知
      内容包含“求片/投稿通过提示”以及“获得的奖励”信息（若可查到）
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主控消息服务
    
    返回值:
    - None
    """
    await callback.answer("🚀 正在推送，请稍候...")

    sent_count = 0
    fail_count = 0

    # 获取所有待发送的通知
    stmt = select(LibraryNewNotificationModel).where(
        LibraryNewNotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
        LibraryNewNotificationModel.type == EVENT_TYPE_LIBRARY_NEW
    )
    result = await session.execute(stmt)
    notifications = result.scalars().all()

    if not notifications:
        await callback.answer("🈚 没有可发送的通知", show_alert=True)
        # 返回面板
        await show_notification_panel(callback, session, main_msg)
        return

    # 获取目标频道ID列表
    target_chat_ids = []
    
    # 从数据库读取配置
    # 结构: [{"id": "123", "name": "foo", "enabled": True}, ...]
    channels_config = await get_config(session, KEY_NOTIFICATION_CHANNELS)
    if channels_config and isinstance(channels_config, list):
        for ch in channels_config:
            if isinstance(ch, dict) and ch.get("enabled"):
                target_chat_ids.append(ch["id"])
    
    # 兼容旧代码：如果数据库没配置，尝试从 settings 获取 (虽然启动时已经 sync 了，但为了双重保险)
    if not target_chat_ids:
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

            msg_text, image_url = await get_notification_content(item, session)

            # 合并目标频道：配置的频道 + 通知原有的target_channel_id
            all_target_chat_ids = list(target_chat_ids)  # 从配置获取的频道

            # 如果通知本身有target_user_id，也要发送给这些人
            if notif.target_user_id:
                try:
                    # 解析原有的target_user_id（逗号分隔的字符串）
                    existing_targets = [int(x.strip()) for x in notif.target_user_id.split(",") if x.strip()]
                    # 添加到目标列表中，避免重复
                    for target in existing_targets:
                        if target not in all_target_chat_ids:
                            all_target_chat_ids.append(target)
                except ValueError as e:
                    logger.warning(f"⚠️ 解析通知的target_user_id失败: {notif.target_user_id} -> {e}")

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
        f"*{ADMIN_NEW_ITEM_NOTIFICATION_LABEL}*\n\n"
        f"📊 *状态统计:*\n"
        f"• 待补全：*{pending_completion}*\n"
        f"• 待发送：*{pending_review}*\n\n"
        f"✅ *操作完成：* 成功 {sent_count}, 失败 {fail_count}\n"
    )
    kb = get_notification_panel_keyboard(pending_completion, pending_review)
    await main_msg.update_on_callback(callback, text, kb)
