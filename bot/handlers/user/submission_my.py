from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import UserSubmissionModel, MediaCategoryModel
from bot.keyboards.inline.buttons import BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import USER_SUBMISSION_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.text import escape_markdown_v2

router = Router(name="user_submission_my")

@router.callback_query(F.data == f"{USER_SUBMISSION_CALLBACK_DATA}:my_submissions")
async def my_submissions(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """查看我的求片/投稿"""
    
    user_id = callback.from_user.id
    
    # 获取用户的所有提交记录
    stmt = (
        select(UserSubmissionModel, MediaCategoryModel)
        .join(MediaCategoryModel, UserSubmissionModel.category_id == MediaCategoryModel.id)
        .where(UserSubmissionModel.submitter_id == user_id)
        .where(UserSubmissionModel.is_deleted == False)
        .order_by(desc(UserSubmissionModel.created_at))
        .limit(20)
    )
    
    result = await session.execute(stmt)
    submissions = result.all()
    
    if not submissions:
        text = (
            "*📋 我的求片/投稿*\n\n"
            "您还没有任何求片或投稿记录。\n\n"
        "点击下方按钮开始您的第一次求片或投稿吧\\!"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📥 开始求片", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:request")
        builder.button(text="✍️ 开始投稿", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:submit")
        builder.row(BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON)
        
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
            "request": "📥",
            "submit": "✍️"
        }.get(submission.type, "📝")
        
        # 状态文本
        status_text = {
            "pending": "待审核",
            "approved": "已通过", 
            "rejected": "已拒绝"
        }.get(submission.status, "未知")
        
        line = (
            f"{status_icon} {type_icon} **#{submission.id}** {escape_markdown_v2(submission.title)}\n"
            f"🏷️ {escape_markdown_v2(category.name)} · {status_text}\n"
            f"📅 {submission.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # 检查是否有图片
        has_image = submission.extra and submission.extra.get("has_image", False)
        if has_image:
            line += " · 📷"
        
        if submission.reward_base > 0 or submission.reward_bonus > 0:
            total_reward = submission.reward_base + submission.reward_bonus
            line += f" · 🎁 +{total_reward}"
        
        lines.append(line)
        lines.append("")  # 空行分隔
    
    text = "\n".join(lines)
    
    # 创建键盘
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 开始求片", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:request")
    builder.button(text="✍️ 开始投稿", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:submit")
    builder.row(BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON)
    
    await main_msg.update_on_callback(callback, text, builder.as_markup())
    await callback.answer()