from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.buttons import BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import USER_SUBMISSION_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.user import UserSubmissionState

router = Router(name="user_submission")

@router.callback_query(F.data == USER_SUBMISSION_CALLBACK_DATA)
async def start_submission(callback: CallbackQuery, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """开始求片/投稿主界面"""
    
    text = (
        "*📝 求片/投稿中心*\n\n"
        "请选择您要进行的操作：\n\n"
        "📥 *开始求片* - 提交您想要的影片\n"
        "✍️ *开始投稿* - 提交您发现的优质内容\n"
        "📝 *问答投稿* - 为题库贡献题目\n"
        "📋 *我的求片/投稿* - 查看您的提交记录"
    )
    
    # 创建键盘
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 开始求片", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:request")
    builder.button(text="✍️ 开始投稿", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:submit")
    builder.button(text="📝 问答投稿", callback_data="user:quiz:submit")  # 保留原有的问答投稿入口
    builder.button(text="📋 我的求片/投稿", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:my_submissions")
    builder.row(BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON)
    builder.adjust(1)  # 每行一个按钮
    
    await main_msg.update_on_callback(callback, text, builder.as_markup())
    await callback.answer()