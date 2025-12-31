from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.quiz_service import QuizService
from bot.utils.permissions import require_admin_feature


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":test_trigger")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def test_trigger(callback: CallbackQuery, session: AsyncSession) -> None:
    """测试触发题目"""
    user_id = callback.from_user.id
    # 强制给管理员私聊发送
    target_chat_id = user_id

    try:
        # 强制触发，不检查条件
        quiz_data = await QuizService.create_quiz_session(session, user_id, target_chat_id)
        if quiz_data:
            question, image, markup, session_id = quiz_data
            caption = await QuizService.build_quiz_caption(
                question=question,
                image=image,
                session=session
            )
            bot = callback.bot
            if image:
                sent = await bot.send_photo(target_chat_id, image.file_id, caption=caption, reply_markup=markup)
            else:
                sent = await bot.send_message(target_chat_id, caption, reply_markup=markup)

            await QuizService.update_session_message_id(session, session_id, sent.message_id)
        else:
            await callback.answer("⚠️ 题库为空或生成失败。")

    except Exception as e:
        await callback.message.answer(f"❌ 测试失败: {e}")
