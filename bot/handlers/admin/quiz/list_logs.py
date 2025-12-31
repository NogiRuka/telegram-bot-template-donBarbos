from aiogram import F
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizLogModel
from bot.keyboards.inline.admin import get_quiz_list_keyboard
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":list_logs")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def list_logs(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示问答记录列表"""
    # 只显示最近 10 条
    stmt = select(QuizLogModel).order_by(QuizLogModel.id.desc()).limit(10)
    logs = (await session.execute(stmt)).scalars().all()

    msg = "*📜 最近问答记录 \\(Top 10\\):*\n\n"
    for log in logs:
        status = "✅ 正确" if log.is_correct else "❌ 错误"
        user_id = log.user_id
        msg += f"ID: {log.id} \\| 用户: {user_id}\n结果: {status}\n\n"

    await main_msg.update_on_callback(callback, msg, get_quiz_list_keyboard())
