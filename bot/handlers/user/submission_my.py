from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserSubmissionModel, MediaCategoryModel
from bot.keyboards.inline.buttons import BACK_TO_USER_SUBMISSION_BUTTON, BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import USER_SUBMISSION_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.text import escape_markdown_v2

router = Router(name="user_submission_my")

@router.callback_query(F.data == f"{USER_SUBMISSION_CALLBACK_DATA}:my_submissions")
async def my_submissions(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """查看我的求片/投稿 - 第一页"""
    await show_submissions_page(callback, session, main_msg, page=1)

@router.callback_query(F.data.regexp(rf"^{USER_SUBMISSION_CALLBACK_DATA}:my_submissions:page:(\d+)$"))
async def my_submissions_page(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """查看我的求片/投稿 - 指定页"""
    # 从回调数据中提取页码
    page_match = callback.data.split(":")[-1]
    page = int(page_match) if page_match.isdigit() else 1
    await show_submissions_page(callback, session, main_msg, page)

async def show_submissions_page(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, page: int = 1) -> None:
    """显示指定页的求片/投稿记录"""
    
    user_id = callback.from_user.id
    items_per_page = 5
    offset = (page - 1) * items_per_page
    
    # 获取用户的提交记录总数
    count_stmt = (
        select(UserSubmissionModel)
        .where(UserSubmissionModel.submitter_id == user_id)
        .where(UserSubmissionModel.is_deleted == False)
    )
    total_count = len((await session.execute(count_stmt)).scalars().all())
    total_pages = (total_count + items_per_page - 1) // items_per_page
    
    # 获取指定页的提交记录
    stmt = (
        select(UserSubmissionModel, MediaCategoryModel)
        .join(MediaCategoryModel, UserSubmissionModel.category_id == MediaCategoryModel.id)
        .where(UserSubmissionModel.submitter_id == user_id)
        .where(UserSubmissionModel.is_deleted == False)
        .order_by(desc(UserSubmissionModel.created_at))
        .offset(offset)
        .limit(items_per_page)
    )
    
    result = await session.execute(stmt)
    submissions = result.all()
    
    if not submissions and page == 1:
        text = (
            "*📋 我的求片/投稿*\n\n"
            "您还没有任何求片或投稿记录。"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(BACK_TO_USER_SUBMISSION_BUTTON, BACK_TO_HOME_BUTTON)
        
        await main_msg.update_on_callback(callback, text, builder.as_markup())
        return
    
    # 构建显示文本
    lines = ["*📋 我的求片/投稿*\n"]
    
    for submission, category in submissions:
        # 状态图标
        status_icon = {
            "pending": "⏳",
            "approved": "✅", 
            "rejected": "❌"
        }.get(submission.status, "❓")
        
        # 类型图标
        type_icon = {
            "request": "🔍",
            "submit": "📥"
        }.get(submission.type, "📝")
        
        # 状态文本
        status_text = {
            "pending": "待审核",
            "approved": "已通过", 
            "rejected": "已拒绝"
        }.get(submission.status, "未知")

        # 显示描述
        desc_text = ""
        if submission.description:
            desc_text = escape_markdown_v2(submission.description[:30])
            if len(submission.description) > 30:
                desc_text += "…"

        line = (
            f"{status_icon} {type_icon} *\\#{submission.id}* `{escape_markdown_v2(submission.title)}`\n"
            f"🏷️ {escape_markdown_v2(category.name)} · {escape_markdown_v2(status_text)}\n"
            f"📅 {escape_markdown_v2(submission.created_at.strftime('%Y-%m-%d %H:%M'))}"
        )

        if desc_text:
            line += f"\n📝 {desc_text}"
        
        # 显示审核者留言（如果有）
        if submission.review_comment and submission.status in ["approved", "rejected"]:
            review_comment = escape_markdown_v2(submission.review_comment[:50])
            if len(submission.review_comment) > 50:
                review_comment += "…"
            line += f"\n💬 {review_comment}"
        
        # 检查是否有图片（使用数据表字段）
        if submission.image_file_id:
            line += " · 📷"
        
        # 显示奖励信息
        if submission.status == "approved":
            # 审核通过后显示总奖励（基础奖励 + 额外奖励）
            if submission.reward_base > 0 or submission.reward_bonus > 0:
                total_reward = submission.reward_base + submission.reward_bonus
                line += f" · 🎁 \\+{total_reward}"
        elif submission.status == "pending":
            # 待审核状态只显示已获得的基础奖励
            if submission.reward_base > 0:
                line += f" · 🎁 \\+{submission.reward_base}"
        else:
            # 其他状态（已拒绝等）显示已获得的基础奖励
            if submission.reward_base > 0:
                line += f" · 🎁 \\+{submission.reward_base}"
        
        lines.append(line)
        lines.append("")  # 空行分隔
    
    # 添加分页信息
    if total_pages > 1:
        lines.append(f"📄 第 {page} 页，共 {total_pages} 页 · 总计 {total_count} 条记录")
    
    text = "\n".join(lines)
    
    # 创建键盘
    builder = InlineKeyboardBuilder()
    
    # 添加分页按钮
    if total_pages > 1:
        pagination_row = []
        
        # 上一页按钮
        if page > 1:
            pagination_row.append(
                InlineKeyboardButton(text="⬅️ 上一页", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:my_submissions:page:{page-1}")
            )
        
        # 页码信息
        pagination_row.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )
        
        # 下一页按钮
        if page < total_pages:
            pagination_row.append(
                InlineKeyboardButton(text="下一页 ➡️", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:my_submissions:page:{page+1}")
            )
        
        builder.row(*pagination_row)
    
    # 添加返回按钮
    builder.row(BACK_TO_USER_SUBMISSION_BUTTON, BACK_TO_HOME_BUTTON)
    
    await main_msg.update_on_callback(callback, text, builder.as_markup())
    await callback.answer()