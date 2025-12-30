from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.database.models import QuizQuestionModel, QuizImageModel
from bot.keyboards.inline.admin import get_quiz_admin_keyboard
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from .router import router

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":list_questions")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_questions(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """显示题目列表"""
    # 只显示最近 10 条
    stmt = select(QuizQuestionModel).order_by(QuizQuestionModel.id.desc()).limit(10)
    questions = (await session.execute(stmt)).scalars().all()
    
    msg = "*📋 最近添加的题目 \\(Top 10\\):*\n\n"
    for q in questions:
        cat_name = q.category.name if q.category else '无分类'
        cat = escape_markdown_v2(cat_name)
        ques = escape_markdown_v2(q.question[:20])
        msg += f"ID: {q.id} \\| {cat}\nQ: {ques}\\.\\.\\.\n\n"
        
    await main_msg.update_on_callback(callback, msg, get_quiz_admin_keyboard()) # 返回菜单

@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":list_images")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_images(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService):
    """显示题图列表"""
    # 只显示最近 10 条
    stmt = select(QuizImageModel).order_by(QuizImageModel.id.desc()).limit(10)
    images = (await session.execute(stmt)).scalars().all()
    
    msg = "*🖼️ 最近添加的图片 \\(Top 10\\):*\n\n"
    for img in images:
        cat_name = img.category.name if img.category else '无分类'
        cat = escape_markdown_v2(cat_name)
        tags_str = ", ".join(img.tags) if img.tags else ""
        tags = escape_markdown_v2(tags_str)
        msg += f"ID: {img.id} \\| {cat}\nTags: {tags}\n\n"
        
    await main_msg.update_on_callback(callback, msg, get_quiz_admin_keyboard())
