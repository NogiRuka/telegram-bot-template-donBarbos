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

from .router import router
from bot.database.models import MediaCategoryModel, UserModel, UserSubmissionModel
from bot.database.models.user_submission import UserSubmissionModel
from bot.keyboards.inline.buttons import BACK_TO_HOME_BUTTON, CLOSE_BUTTON
from bot.services.main_message import MainMessageService
from bot.utils.message import clear_message_list_from_state
from bot.utils.text import escape_markdown_v2

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


def build_submission_review_keyboard() -> InlineKeyboardMarkup:
    """构建投稿审核键盘"""
    # 审核操作改为使用命令进行，此处仅保留关闭按钮
    return InlineKeyboardMarkup(inline_keyboard=[[CLOSE_BUTTON]])


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
        select(UserSubmissionModel, MediaCategoryModel, UserModel)
        .join(MediaCategoryModel, UserSubmissionModel.category_id == MediaCategoryModel.id, isouter=True)
        .join(UserModel, UserSubmissionModel.submitter_id == UserModel.id, isouter=True)
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
    for submission, category, user in submissions:
        try:
            # 构建投稿内容
            category_name = category.name if category else "未分类"
            status_icon = "⏳"  # pending
            type_icon = "📥" if submission.type == "submit" else "🔍"  # submit vs request

            # 构建标题和基本信息
            title = escape_markdown_v2(submission.title)

            # 构建用户显示字符串
            user_display = f"`{submission.submitter_id}`"
            if user and user.username:
                user_display += f" @{escape_markdown_v2(user.username)}"

            caption = (
                f"*{type_icon} {status_icon} 投稿审核 \\#{submission.id}*\n"
                f"📽️ 标题：`{title}`\n"
                f"🏷️ 分类：{escape_markdown_v2(category_name)}\n"
                f"👤 投稿者ID：{user_display}\n"
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
            date_str = escape_markdown_v2(submission.created_at.strftime("%Y-%m-%d %H:%M"))
            caption += f"📅 投稿时间：{date_str}"

            # 构建审核键盘
            keyboard = build_submission_review_keyboard()

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
            logger.error(f"❌ 投稿 #{submission.id} 渲染失败: {e}")
            try:
                error_msg = await callback.message.answer(
                    text=f"⚠️ 投稿 \\#{submission.id} 渲染失败: {escape_markdown_v2(str(e))}",
                    parse_mode="MarkdownV2"
                )
                new_msg_ids.append(error_msg.message_id)
            except Exception as e2:
                logger.error(f"❌ 发送错误通知也失败: {e2}")

    # 记录新发送的消息ID
    await state.update_data(submission_review_ids=new_msg_ids)
    await callback.answer()

