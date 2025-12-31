import builtins
import contextlib

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.quiz_service import QuizService

router = Router(name="user_quiz")

@router.callback_query(F.data.startswith("quiz:ans:"))
async def on_quiz_answer(callback: CallbackQuery, session: AsyncSession) -> None:
    """处理问答点击"""
    try:
        # data format: quiz:ans:{index}
        _, _, index_str = callback.data.split(":")
        answer_index = int(index_str)
        user_id = callback.from_user.id

        # 调用 Service 处理
        # 注意：这里可能会遇到并发问题，比如用户点很快，但 Service 内部有 DB 事务，应该还好。
        # 另外，需要检查这个点击是否属于当前用户。
        # QuizActiveSessionModel 绑定了 user_id。
        # 如果当前没有该用户的 Session，Service 会返回错误。

        _is_correct, _reward, msg = await QuizService.handle_answer(session, user_id, answer_index)

        # 弹窗提示
        await callback.answer(msg, show_alert=True)

        # 编辑原消息：移除键盘，追加结果
        # 注意：如果是图片消息，edit_text 可能报错，应该用 edit_caption
        # 如果是纯文本，用 edit_text
        # 由于我们不知道原消息是图还是文，可以通过 callback.message 类型判断

        result_text = f"\n\n🏁 答题结束\n{msg}"

        if callback.message.photo or callback.message.video or callback.message.document:
            # 带媒体的消息
            original_caption = callback.message.caption or ""
            await callback.message.edit_caption(
                caption=original_caption + result_text,
                reply_markup=None
            )
        else:
            # 纯文本
            original_text = callback.message.text or ""
            await callback.message.edit_text(
                text=original_text + result_text,
                reply_markup=None
            )

    except ValueError:
        await callback.answer("⚠️ 数据异常", show_alert=True)
    except Exception as e:
        # 可能是 Session 已经被删除（超时或已答）
        # 或者消息无法编辑
        await callback.answer(str(e), show_alert=True)
        # 尝试删除键盘以防再次点击
        with contextlib.suppress(builtins.BaseException):
            await callback.message.edit_reply_markup(reply_markup=None)
