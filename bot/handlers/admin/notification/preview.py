import contextlib
from math import ceil

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .router import NotificationStates, router
from bot.core.constants import (
    EVENT_TYPE_LIBRARY_NEW,
    NOTIFICATION_STATUS_PENDING_REVIEW,
    NOTIFICATION_STATUS_REJECTED,
)
from bot.database.models.emby_item import EmbyItemModel
from bot.database.models.library_new_notification import LibraryNewNotificationModel
from bot.keyboards.inline.admin import get_notification_preview_pagination_keyboard
from bot.keyboards.inline.buttons import NOTIFY_CLOSE_PREVIEW_BUTTON
from bot.services.main_message import MainMessageService
from bot.utils.message import clear_message_list_from_state, delete_message, delete_message_after_delay
from bot.utils.notification import get_notification_content


def _has_html_special_chars(text: str | None) -> bool:
    """判断文本是否包含容易破坏 HTML parse_mode 的特殊字符。"""
    if not text:
        return False
    return any(ch in text for ch in "<>&")


def _preview_text(text: str | None, limit: int = 120) -> str:
    """生成日志友好的短预览文本。"""
    if not text:
        return ""
    normalized = text.replace("\r", " ").replace("\n", " ").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "..."


@router.callback_query(F.data.startswith("admin:notify_preview"))
async def handle_notify_preview(
    callback: types.CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    main_msg: MainMessageService
) -> None:
    """生成通知预览 - 每条消息关联具体通知ID"""
    # 解析参数: admin:notify_preview:list:1:5
    # 或者旧入口: admin:notify_preview
    page = 1
    limit = 5

    try:
        parts = callback.data.split(":")
        if len(parts) >= 5 and parts[2] == "list":
            page = int(parts[3])
            limit = int(parts[4])
    except (IndexError, ValueError):
        pass

    # 清理旧消息
    await clear_message_list_from_state(state, callback.bot, callback.message.chat.id, "preview_data")

    preview_key = case(
        (
            (LibraryNewNotificationModel.item_type == "Episode")
            & (LibraryNewNotificationModel.series_id.isnot(None)),
            LibraryNewNotificationModel.series_id,
        ),
        (
            LibraryNewNotificationModel.item_type == "Series",
            LibraryNewNotificationModel.item_id,
        ),
        else_=LibraryNewNotificationModel.item_id,
    )

    subq = (
        select(
            func.min(LibraryNewNotificationModel.id).label("notif_id"),
            preview_key.label("biz_id"),
        )
        .where(
            LibraryNewNotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
            LibraryNewNotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
        )
        .group_by(preview_key)
        .subquery()
    )

    # 查询总数
    count_stmt = select(func.count()).select_from(subq)
    total_count = (await session.execute(count_stmt)).scalar_one()

    total_pages = ceil(total_count / limit) if total_count > 0 else 1
    page = max(1, min(page, total_pages))

    # 分页查询
    stmt = (
        select(LibraryNewNotificationModel, EmbyItemModel)
        .join(subq, LibraryNewNotificationModel.id == subq.c.notif_id)
        .join(EmbyItemModel, EmbyItemModel.id == subq.c.biz_id)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    rows = (await session.execute(stmt)).all()

    if not rows:
        await callback.answer("🈚 没有可预览的通知")

    # 更新主控消息
    text = (
        f"👀 *通知预览*\n\n"
        f"共 {total_count} 条待处理通知\n"
        f"当前第 {page}/{total_pages} 页\n\n"
        f"💡 使用 `/sr` 命令审核"
    )
    kb = get_notification_preview_pagination_keyboard(page, total_pages, limit)
    await main_msg.update_on_callback(callback, text, kb)

    # 存储预览消息信息：{message_id: notification_id}
    preview_data = {}

    for notif, item in rows:
        msg_text, image_url = await get_notification_content(item, session)

        # 创建操作键盘
        status_text = "🔄 " + ("更新中" if item.status == "Continuing" else "已完结") + f"（{notif.id}）"
        reject_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🚫 拒绝", callback_data=f"admin:notify_reject:{notif.id}"),
                    InlineKeyboardButton(text="👥 添加", callback_data=f"admin:notify_add_sender:{notif.id}"),
                    InlineKeyboardButton(text=status_text, callback_data=f"admin:notify_toggle_status:{notif.id}")
                ],
                [NOTIFY_CLOSE_PREVIEW_BUTTON]
            ]
        )

        try:
            msg = None
            raw_name = notif.item_name or notif.series_name or item.name or "Unknown"
            raw_overview = item.overview or ""
            if image_url:
                logger.debug(f"正在发送图片预览: {image_url}")
                try:
                    msg = await callback.bot.send_photo(
                        callback.from_user.id,
                        photo=image_url,
                        caption=msg_text,
                        reply_markup=reject_kb,
                    )
                except Exception as e:
                    logger.warning(
                        "图片发送失败，尝试转为纯文本发送 | "
                        f"Notification ID: {notif.id} | "
                        f"Item ID: {item.id} | "
                        f"URL: {image_url} | "
                        f"NameHasHtmlChars: {_has_html_special_chars(raw_name)} | "
                        f"OverviewHasHtmlChars: {_has_html_special_chars(raw_overview)} | "
                        f"NamePreview: {_preview_text(raw_name)} | "
                        f"OverviewPreview: {_preview_text(raw_overview)} | "
                        f"Error: {e}"
                    )
                    # 图片发送失败（如 wrong type of the web page content），回退到发送纯文本

            if not msg:
                msg = await callback.bot.send_message(
                    callback.from_user.id,
                    msg_text,
                    reply_markup=reject_kb,
                )

            # 关联消息ID和通知ID
            preview_data[msg.message_id] = notif.id

        except Exception as e:
            error_info = (
                f"预览发送失败 | "
                f"Notification ID: {notif.id} | "
                f"Item ID: {item.id} | "
                f"Name: {raw_name} | "
                f"NameHasHtmlChars: {_has_html_special_chars(raw_name)} | "
                f"OverviewHasHtmlChars: {_has_html_special_chars(raw_overview)} | "
                f"NamePreview: {_preview_text(raw_name)} | "
                f"OverviewPreview: {_preview_text(raw_overview)} | "
                f"Error: {e}"
            )
            logger.error(error_info)
            # 发送错误提示给用户，方便定位问题
            with contextlib.suppress(Exception):
                await callback.bot.send_message(
                    callback.from_user.id,
                    f"⚠️ 预览发送出错:\nID: {notif.id}\nName: {notif.item_name or notif.series_name}\nError: {str(e)[:100]}"
                )

    # 存储预览数据到FSM状态
    await state.update_data(preview_data=preview_data)


@router.callback_query(F.data.startswith("admin:notify_reject:"))
async def handle_notify_reject(
    callback: types.CallbackQuery,
    session: AsyncSession
) -> None:
    """拒绝单条通知 - 将指定通知状态改为rejected"""
    # 从callback_data中提取通知ID
    try:
        notification_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("无效的请求", show_alert=True)
        return

    # 获取指定通知
    stmt = select(LibraryNewNotificationModel).where(
        LibraryNewNotificationModel.id == notification_id,
        LibraryNewNotificationModel.status == NOTIFICATION_STATUS_PENDING_REVIEW,
        LibraryNewNotificationModel.type == EVENT_TYPE_LIBRARY_NEW,
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


@router.callback_query(F.data.startswith("admin:notify_toggle_status:"))
async def handle_item_status_toggle(
    callback: types.CallbackQuery,
    session: AsyncSession
) -> None:
    """切换 Emby Item 状态 (Continuing <-> Ended)"""
    try:
        notif_id = int(callback.data.split(":")[2])

        # 1. 获取 Notification
        notif = await session.get(LibraryNewNotificationModel, notif_id)
        if not notif:
            await callback.answer("❌ 通知不存在", show_alert=True)
            return

        # 2. 确定 Emby Item ID
        # 逻辑需与 handle_notify_preview 中的 join 条件一致
        # Episode 且有 series_id -> series_id
        # 否则 -> item_id
        target_item_id = notif.series_id if notif.item_type == "Episode" and notif.series_id else notif.item_id

        if not target_item_id:
             await callback.answer("❌ 无法确定关联的媒体项 ID", show_alert=True)
             return

        # 3. 获取 Emby Item
        item = await session.get(EmbyItemModel, target_item_id)
        if not item:
            await callback.answer("❌ 关联的媒体项不存在", show_alert=True)
            return

        # 4. 切换状态
        current_status = item.status
        new_status = "Ended" if current_status == "Continuing" else "Continuing"
        item.status = new_status
        session.add(item)
        await session.commit()

        # 5. 更新界面
        # 重新生成文案
        msg_text, _ = await get_notification_content(item, session)

        # 重新生成键盘
        status_text = "🔄 " + ("已完结" if item.status == "Ended" else "更新中") + f"（{notif.id}）"
        new_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🚫 拒绝", callback_data=f"admin:notify_reject:{notif.id}"),
                    InlineKeyboardButton(text="👥 添加", callback_data=f"admin:notify_add_sender:{notif.id}"),
                    InlineKeyboardButton(text=status_text, callback_data=f"admin:notify_toggle_status:{notif.id}")
                ],
                [NOTIFY_CLOSE_PREVIEW_BUTTON]
            ]
        )

        # 更新消息
        if callback.message.photo:
            await callback.message.edit_caption(caption=msg_text, reply_markup=new_kb)
        else:
            await callback.message.edit_text(text=msg_text, reply_markup=new_kb)

        await callback.answer(f"✅ 状态已切换为 {new_status}")

    except Exception as e:
        logger.error(f"切换状态失败: {e}")
        await callback.answer("❌ 操作失败", show_alert=True)


@router.callback_query(F.data.startswith("admin:notify_add_sender:"))
async def handle_add_sender_start(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """开始添加通知者流程"""

    # 从callback_data中提取通知ID
    try:
        notification_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.answer("无效的请求", show_alert=True)
        return

    # 存储通知ID到状态
    await state.update_data(notification_id=notification_id)
    await state.set_state(NotificationStates.waiting_for_additional_sender)

    await callback.answer(
        "请输入要添加的通知者信息（可以是用户ID、用户名等）：\n"
        "或者直接回复消息来引用用户"
    )


@router.message(NotificationStates.waiting_for_additional_sender)
async def handle_add_sender_complete(
    message: types.Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """处理添加通知者的输入

    功能说明:
    - 将管理员输入的用户标识保存到 LibraryNewNotificationModel.target_user__id
    - 支持追加多个用户ID，使用逗号分隔

    输入参数:
    - message: 当前消息对象
    - session: 异步数据库会话
    - state: FSM 状态上下文

    返回值:
    - None
    """
    data = await state.get_data()
    notification_id = data.get("notification_id")

    if not notification_id:
        await message.answer("❌ 状态错误，请重新操作")
        await state.clear()
        return

    # 获取通知
    stmt = select(LibraryNewNotificationModel).where(LibraryNewNotificationModel.id == notification_id)
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

    # 获取当前的目标用户ID列表
    current_senders = notification.target_user_id or ""

    # 添加新的目标用户ID
    new_senders = f"{current_senders},{sender_info}" if current_senders else sender_info

    notification.target_user_id = new_senders
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
