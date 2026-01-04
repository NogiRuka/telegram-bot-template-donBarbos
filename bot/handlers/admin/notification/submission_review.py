"""
投稿审核功能
参考题库预览实现，提供投稿内容的审核管理
"""
from math import ceil

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserSubmissionModel, MediaCategoryModel
from bot.database.models.user_submission import UserSubmissionModel
from bot.keyboards.inline.buttons import BACK_TO_HOME_BUTTON, CLOSE_BUTTON
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.utils.message import delete_message, clear_message_list_from_state
from bot.utils.text import escape_markdown_v2
from bot.core.constants import CURRENCY_SYMBOL

from .router import router
from .states import NotificationReviewStates

# 回调数据前缀
SUBMISSION_REVIEW_CALLBACK_DATA = "admin:submission_review"
SUBMISSION_REVIEW_LIST_CALLBACK_DATA = "admin:submission_review:list"
SUBMISSION_REVIEW_APPROVE_CALLBACK_DATA = "admin:submission_review:approve"
SUBMISSION_REVIEW_REJECT_CALLBACK_DATA = "admin:submission_review:reject"
SUBMISSION_REVIEW_APPROVE_WITH_COMMENT_CALLBACK_DATA = "admin:submission_review:approve_with_comment"
SUBMISSION_REVIEW_REJECT_WITH_COMMENT_CALLBACK_DATA = "admin:submission_review:reject_with_comment"
SUBMISSION_REVIEW_CANCEL_CALLBACK_DATA = "admin:submission_review:cancel"


def get_submission_review_pagination_keyboard(page: int, total_pages: int, limit: int = 5) -> InlineKeyboardMarkup:
    """生成分页键盘"""
    builder = InlineKeyboardBuilder()

    # 上一页
    if page > 1:
        builder.button(
            text="⬅️ 上一页",
            callback_data=f"{SUBMISSION_REVIEW_LIST_CALLBACK_DATA}:{page - 1}:{limit}"
        )
    else:
        builder.button(text="⛔️", callback_data="ignore")
    
    # 页码指示 (Toggle limit)
    next_limit = 10 if limit == 5 else (20 if limit == 10 else 5)
    builder.button(
        text=f"{page}/{total_pages} (每页{limit:02d}条)",
        callback_data=f"{SUBMISSION_REVIEW_LIST_CALLBACK_DATA}:1:{next_limit}"
    )

    # 下一页
    if page < total_pages:
        builder.button(
            text="下一页 ➡️",
            callback_data=f"{SUBMISSION_REVIEW_LIST_CALLBACK_DATA}:{page + 1}:{limit}"
        )
    else:
        builder.button(text="⛔️", callback_data="ignore")
    
    builder.adjust(3)
    
    # 返回按钮
    builder.row(
        InlineKeyboardButton(text="🔙 返回通知面板", callback_data="admin:new_item_notification"),
        BACK_TO_HOME_BUTTON
    )
    
    return builder.as_markup()


def build_submission_review_keyboard(submission_id: int, status: str, is_review_needed: bool = True) -> InlineKeyboardMarkup:
    """构建投稿审核键盘"""
    if not is_review_needed:
        return InlineKeyboardMarkup(inline_keyboard=[[CLOSE_BUTTON]])
    
    buttons = []
    
    # 第一行：基本审核操作
    if status == "pending":
        buttons.append([
            InlineKeyboardButton(text="✅ 通过", callback_data=f"{SUBMISSION_REVIEW_APPROVE_CALLBACK_DATA}:{submission_id}"),
            InlineKeyboardButton(text="❌ 拒绝", callback_data=f"{SUBMISSION_REVIEW_REJECT_CALLBACK_DATA}:{submission_id}"),
        ])
        
        # 第二行：带留言的审核操作
        buttons.append([
            InlineKeyboardButton(text="✅ 通过并留言", callback_data=f"{SUBMISSION_REVIEW_APPROVE_WITH_COMMENT_CALLBACK_DATA}:{submission_id}"),
            InlineKeyboardButton(text="❌ 拒绝并留言", callback_data=f"{SUBMISSION_REVIEW_REJECT_WITH_COMMENT_CALLBACK_DATA}:{submission_id}"),
        ])
    
    # 关闭按钮
    buttons.append([CLOSE_BUTTON])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "admin:submission_review")
async def show_submission_review_panel(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
    state: FSMContext
) -> None:
    """显示投稿审核面板"""
    await clear_message_list_from_state(state, callback.bot, callback.message.chat.id, "submission_review_ids")

    # 计算待审核数量
    count_stmt = select(func.count()).select_from(UserSubmissionModel).where(
        UserSubmissionModel.status == "pending"
    )
    pending_count = (await session.execute(count_stmt)).scalar_one()

    text = (
        f"*🎬 求片/投稿审核*\n\n"
        f"📊 *统计信息:*\n"
        f"• 待审核投稿：*{pending_count}*"
    )
    
    # 创建审核键盘
    builder = InlineKeyboardBuilder()
    if pending_count > 0:
        builder.button(text=f"📋 开始审核 ({pending_count})", callback_data=f"{SUBMISSION_REVIEW_LIST_CALLBACK_DATA}:1:5")
    else:
        builder.button(text="✅ 暂无待审核", callback_data="ignore")
    
    builder.row(
        InlineKeyboardButton(text="🔙 返回通知面板", callback_data="admin:new_item_notification"),
        BACK_TO_HOME_BUTTON
    )
    
    await main_msg.update_on_callback(callback, text, builder.as_markup())


@router.callback_query(F.data.startswith(SUBMISSION_REVIEW_LIST_CALLBACK_DATA + ":"))
async def list_submissions_for_review(
    callback: types.CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
    state: FSMContext
) -> None:
    """显示待审核投稿列表（分页）"""
    # 解析参数: admin:submission_review:list:1:5
    try:
        parts = callback.data.split(":")
        page = int(parts[3])
        limit = int(parts[4])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    # 清理旧消息
    await clear_message_list_from_state(state, callback.bot, callback.message.chat.id, "submission_review_ids")

    # 计算总数
    count_stmt = select(func.count()).select_from(UserSubmissionModel).where(
        UserSubmissionModel.status == "pending"
    )
    total_count = (await session.execute(count_stmt)).scalar_one()
    total_pages = ceil(total_count / limit) if total_count > 0 else 1

    # 如果页码超出范围则调整
    page = min(page, total_pages)
    page = max(page, 1)

    # 查询待审核投稿
    stmt = (
        select(UserSubmissionModel, MediaCategoryModel)
        .join(MediaCategoryModel, UserSubmissionModel.category_id == MediaCategoryModel.id, isouter=True)
        .where(UserSubmissionModel.status == "pending")
        .order_by(UserSubmissionModel.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    submissions = (await session.execute(stmt)).all()

    # 更新主控消息
    text = (
        f"*📋 投稿审核列表*\n\n"
        f"共 {total_count} 条待审核，当前第 {page}/{total_pages} 页"
    )
    kb = get_submission_review_pagination_keyboard(page, total_pages, limit)
    await main_msg.update_on_callback(callback, text, kb)

    if not submissions:
        await callback.answer("🈚 暂无待审核投稿")
        return

    new_msg_ids = []
    for submission, category in submissions:
        try:
            # 构建投稿内容
            category_name = category.name if category else "未分类"
            status_icon = "⏳"  # pending
            type_icon = "📥" if submission.type == "submit" else "🔍"  # submit vs request
            
            # 构建标题和基本信息
            title = escape_markdown_v2(submission.title)
            caption = (
                f"*{type_icon} {status_icon} 投稿审核 \\#{submission.id}*\n"
                f"📽️ 标题：`{title}`\n"
                f"🏷️ 分类：{escape_markdown_v2(category_name)}\n"
                f"👤 投稿者ID：`{submission.submitter_id}`\n"
            )
            
            # 添加描述（如果有）
            if submission.description:
                desc = escape_markdown_v2(submission.description[:200])
                if len(submission.description) > 200:
                    desc += "…"
                caption += f"📝 描述：{desc}\n"
            
            # 添加奖励信息
            if submission.reward_base > 0 or submission.reward_bonus > 0:
                caption += f"💰 奖励：基础\\+{submission.reward_base}"
                if submission.reward_bonus > 0:
                    caption += f"，额外\\+{submission.reward_bonus}"
                caption += "\n"
            
            # 添加时间信息
            date_str = escape_markdown_v2(submission.created_at.strftime('%Y-%m-%d %H:%M'))
            caption += f"📅 投稿时间：{date_str}"

            # 构建审核键盘
            keyboard = build_submission_review_keyboard(submission.id, submission.status)

            # 发送消息
            if submission.image_file_id:
                # 有图片，发送图片消息
                msg = await callback.message.answer_photo(
                    photo=submission.image_file_id,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="MarkdownV2"
                )
            else:
                # 无图片，发送文本消息
                msg = await callback.message.answer(
                    text=caption,
                    reply_markup=keyboard,
                    parse_mode="MarkdownV2"
                )
            
            new_msg_ids.append(msg.message_id)

        except Exception as e:
            logger.error(f"投稿 #{submission.id} 渲染失败: {e}")
            try:
                error_msg = await callback.message.answer(
                    text=f"⚠️ 投稿 \\#{submission.id} 渲染失败: {escape_markdown_v2(str(e))}",
                    parse_mode="MarkdownV2"
                )
                new_msg_ids.append(error_msg.message_id)
            except Exception as e2:
                logger.error(f"发送错误通知也失败: {e2}")

    # 记录新发送的消息ID
    await state.update_data(submission_review_ids=new_msg_ids)
    await callback.answer()


@router.callback_query(F.data.startswith(SUBMISSION_REVIEW_APPROVE_CALLBACK_DATA + ":"))
async def approve_submission(
    callback: types.CallbackQuery,
    session: AsyncSession
) -> None:
    """通过投稿审核"""
    try:
        submission_id = int(callback.data.split(":")[3])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    submission = await session.get(UserSubmissionModel, submission_id)
    if not submission:
        await callback.answer("❌ 投稿不存在", show_alert=True)
        return

    if submission.status != "pending":
        await callback.answer("❌ 投稿状态已改变", show_alert=True)
        return

    try:
        # 更新投稿状态
        submission.status = "approved"
        submission.reviewer_id = callback.from_user.id
        submission.review_time = callback.message.date.strftime("%Y-%m-%d %H:%M:%S")

        # 发放奖励（如果有额外奖励）
        if submission.reward_bonus > 0:
            await CurrencyService.add_currency(
                session=session,
                user_id=submission.submitter_id,
                amount=submission.reward_bonus,
                event_type="submission_approve",
                description=f"投稿 #{submission.id} 审核通过奖励"
            )

        await session.commit()

        # 通知投稿者
        try:
            type_text = "投稿" if submission.type == "submit" else "求片"
            await callback.bot.send_message(
                submission.submitter_id,
                f"🎉 *恭喜\!* 您的{type_text} *{escape_markdown_v2(submission.title)}* 已通过审核\!\n"
                f"{'🎁 获得额外奖励：\\+' + str(submission.reward_bonus) + ' ' + escape_markdown_v2(CURRENCY_SYMBOL) + '\\n' if submission.reward_bonus > 0 else ''}"
                f"💡 感谢您的贡献\!",
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logger.warning(f"通知投稿者 {submission.submitter_id} 失败: {e}")

        # 更新键盘
        keyboard = build_submission_review_keyboard(submission.id, "approved", is_review_needed=False)
        await callback.message.edit_reply_markup(reply_markup=keyboard)

        await callback.answer(f"✅ 已通过投稿 #{submission.id}")

    except Exception as e:
        logger.error(f"通过投稿失败: {e}")
        await callback.answer(f"❌ 操作失败: {e}", show_alert=True)


@router.callback_query(F.data.startswith(SUBMISSION_REVIEW_REJECT_CALLBACK_DATA + ":"))
async def reject_submission(
    callback: types.CallbackQuery,
    session: AsyncSession
) -> None:
    """拒绝投稿审核"""
    try:
        submission_id = int(callback.data.split(":")[3])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    submission = await session.get(UserSubmissionModel, submission_id)
    if not submission:
        await callback.answer("❌ 投稿不存在", show_alert=True)
        return

    if submission.status != "pending":
        await callback.answer("❌ 投稿状态已改变", show_alert=True)
        return

    try:
        # 更新投稿状态
        submission.status = "rejected"
        submission.reviewer_id = callback.from_user.id
        submission.review_time = callback.message.date.strftime("%Y-%m-%d %H:%M:%S")

        await session.commit()

        # 通知投稿者
        try:
            type_text = "投稿" if submission.type == "submit" else "求片"
            await callback.bot.send_message(
                submission.submitter_id,
                f"⚠️ *很遗憾*，您的{type_text} *{escape_markdown_v2(submission.title)}* 未通过审核。\n"
                f"💡 请检查内容是否符合要求，可重新提交。",
                parse_mode="MarkdownV2"
            )
        except Exception as e:
            logger.warning(f"通知投稿者 {submission.submitter_id} 失败: {e}")

        # 更新键盘
        keyboard = build_submission_review_keyboard(submission.id, "rejected", is_review_needed=False)
        await callback.message.edit_reply_markup(reply_markup=keyboard)

        await callback.answer(f"❌ 已拒绝投稿 #{submission.id}")

    except Exception as e:
        logger.error(f"拒绝投稿失败: {e}")
        await callback.answer(f"❌ 操作失败: {e}", show_alert=True)


@router.callback_query(F.data.startswith(SUBMISSION_REVIEW_APPROVE_WITH_COMMENT_CALLBACK_DATA + ":"))
async def approve_submission_with_comment_start(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """开始通过并留言流程"""
    try:
        submission_id = int(callback.data.split(":")[3])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    # 保存上下文
    await state.update_data(
        review_submission_id=submission_id,
        review_action="approve_with_comment",
        review_msg_id=callback.message.message_id
    )
    await state.set_state(NotificationReviewStates.waiting_for_review_comment)

    # 提示输入留言
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ 取消", callback_data=SUBMISSION_REVIEW_CANCEL_CALLBACK_DATA)
    
    await callback.message.reply(
        "📝 请输入通过留言（将发送给投稿者）：",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith(SUBMISSION_REVIEW_REJECT_WITH_COMMENT_CALLBACK_DATA + ":"))
async def reject_submission_with_comment_start(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """开始拒绝并留言流程"""
    try:
        submission_id = int(callback.data.split(":")[3])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    # 保存上下文
    await state.update_data(
        review_submission_id=submission_id,
        review_action="reject_with_comment",
        review_msg_id=callback.message.message_id
    )
    await state.set_state(NotificationReviewStates.waiting_for_review_comment)

    # 提示输入留言
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ 取消", callback_data=SUBMISSION_REVIEW_CANCEL_CALLBACK_DATA)
    
    await callback.message.reply(
        "📝 请输入拒绝原因（将发送给投稿者）：",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == SUBMISSION_REVIEW_CANCEL_CALLBACK_DATA)
async def cancel_review_with_comment(
    callback: types.CallbackQuery,
    state: FSMContext
) -> None:
    """取消审核留言"""
    await state.set_state(None)
    # 删除提示消息
    await delete_message(callback)
    await callback.answer("已取消")


@router.message(NotificationReviewStates.waiting_for_review_comment)
async def process_review_comment(
    message: types.Message,
    session: AsyncSession,
    state: FSMContext
) -> None:
    """处理审核留言"""
    comment = message.text.strip()
    if not comment:
        await message.answer("⚠️ 留言不能为空")
        return
        
    if len(comment) > 500:
        await message.answer("⚠️ 留言过长（最多500字）")
        return

    data = await state.get_data()
    submission_id = data.get("review_submission_id")
    action = data.get("review_action")
    msg_id = data.get("review_msg_id")

    # 删除用户输入的消息，保持对话框清洁
    await delete_message(message)

    if not submission_id or not action:
        await message.answer("❌ 状态错误，请重新操作")
        await state.clear()
        return

    submission = await session.get(UserSubmissionModel, submission_id)
    if not submission:
        await message.answer("❌ 投稿不存在")
        await state.clear()
        return

    if submission.status != "pending":
        await message.answer("❌ 投稿状态已改变")
        await state.clear()
        return

    try:
        # 根据action执行相应操作
        if action == "approve_with_comment":
            submission.status = "approved"
            submission.reviewer_id = message.from_user.id
            submission.review_time = message.date.strftime("%Y-%m-%d %H:%M:%S")
            submission.review_comment = comment

            # 发放奖励（如果有额外奖励）
            if submission.reward_bonus > 0:
                await CurrencyService.add_currency(
                    session=session,
                    user_id=submission.submitter_id,
                    amount=submission.reward_bonus,
                    event_type="submission_approve",
                    description=f"投稿 #{submission.id} 审核通过奖励"
                )

            # 通知投稿者
            try:
                type_text = "投稿" if submission.type == "submit" else "求片"
                await message.bot.send_message(
                    submission.submitter_id,
                    f"🎉 *恭喜\\!* 您的{type_text} *{escape_markdown_v2(submission.title)}* 已通过审核\\!\\n"
                    f"💬 审核留言：{escape_markdown_v2(comment)}\\n"
                    f"{'🎁 获得额外奖励：\\+' + str(submission.reward_bonus) + ' ' + escape_markdown_v2(CURRENCY_SYMBOL) + '\\n' if submission.reward_bonus > 0 else ''}"
                    f"💡 感谢您的贡献\\!",
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.warning(f"通知投稿者 {submission.submitter_id} 失败: {e}")

            success_text = f"✅ 已通过投稿 #{submission.id}，留言已发送"

        elif action == "reject_with_comment":
            submission.status = "rejected"
            submission.reviewer_id = message.from_user.id
            submission.review_time = message.date.strftime("%Y-%m-%d %H:%M:%S")
            submission.review_comment = comment

            # 通知投稿者
            try:
                type_text = "投稿" if submission.type == "submit" else "求片"
                await message.bot.send_message(
                    submission.submitter_id,
                    f"⚠️ *很遗憾*，您的{type_text} *{escape_markdown_v2(submission.title)}* 未通过审核。\n"
                    f"📝 拒绝原因：{escape_markdown_v2(comment)}\n"
                    f"💡 请根据反馈修改后重新提交。",
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.warning(f"通知投稿者 {submission.submitter_id} 失败: {e}")

            success_text = f"❌ 已拒绝投稿 #{submission.id}，原因已发送"

        await session.commit()

        # 发送成功消息
        success_msg = await message.answer(success_text)
        
        # 3秒后删除成功消息
        from bot.utils.message import delete_message_after_delay
        delete_message_after_delay(success_msg)

    except Exception as e:
        logger.error(f"审核操作失败: {e}")
        await message.answer(f"❌ 操作失败: {e}")

    finally:
        await state.clear()