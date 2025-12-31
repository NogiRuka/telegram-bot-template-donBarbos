import builtins
import contextlib

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.quiz_service import QuizService, QuizSessionExpiredError
from bot.utils.message import safe_delete_message

router = Router(name="user_quiz")

@router.callback_query(F.data.startswith("quiz:ans:"))
async def on_quiz_answer(callback: CallbackQuery, session: AsyncSession) -> None:  # noqa: PLR0915
    """处理问答点击"""
    try:
        # data format: quiz:ans:{index}
        _, _, index_str = callback.data.split(":")
        answer_index = int(index_str)
        user_id = callback.from_user.id

        _is_correct, _reward, msg, original_caption = await QuizService.handle_answer(session, user_id, answer_index)

        # 编辑原消息: 移除键盘, 追加结果
        # 注意: 如果是图片消息, edit_text 可能报错, 应该用 edit_caption
        # 如果是纯文本, 用 edit_text
        # 由于我们不知道原消息是图还是文, 可以通过 callback.message 类型判断

        result_text = f"\n\n{msg}"

        # 关闭键盘按钮
        close_kb = InlineKeyboardBuilder()
        close_kb.button(text="❌ 关闭", callback_data="quiz:close")
        reply_kb = close_kb.as_markup()

        if callback.message.photo or callback.message.video or callback.message.document:
            # 带媒体的消息
            await callback.message.edit_caption(
                caption=original_caption + result_text,
                reply_markup=reply_kb,
                parse_mode="HTML"
            )
        else:
            # 纯文本
            await callback.message.edit_text(
                text=original_caption + result_text,
                reply_markup=reply_kb,
                parse_mode="HTML"
            )

    except QuizSessionExpiredError as e:
        # 会话已过期, 编辑消息显示提示, 不使用弹窗
        hint = f"\n\n⏰ {e.message}"
        close_kb = InlineKeyboardBuilder()
        close_kb.button(text="❌ 关闭", callback_data="quiz:close")
        reply_kb = close_kb.as_markup()
        with contextlib.suppress(builtins.BaseException):
            if callback.message.photo or callback.message.video or callback.message.document:
                original_caption = callback.message.caption or ""
                await callback.message.edit_caption(
                    caption=original_caption + hint,
                    reply_markup=reply_kb,
                    parse_mode="HTML"
                )
            else:
                original_text = callback.message.text or ""
                await callback.message.edit_text(
                    text=original_text + hint,
                    reply_markup=reply_kb,
                    parse_mode="HTML"
                )
        with contextlib.suppress(builtins.BaseException):
            await callback.answer()

    except ValueError:
        # 编辑消息显示数据异常提示
        hint = "\n\n⚠️ 数据异常"
        close_kb = InlineKeyboardBuilder()
        close_kb.button(text="❌ 关闭", callback_data="quiz:close")
        reply_kb = close_kb.as_markup()
        with contextlib.suppress(builtins.BaseException):
            if callback.message.photo or callback.message.video or callback.message.document:
                original_caption = callback.message.caption or ""
                await callback.message.edit_caption(
                    caption=original_caption + hint,
                    reply_markup=reply_kb
                )
            else:
                original_text = callback.message.text or ""
                await callback.message.edit_text(
                    text=original_text + hint,
                    reply_markup=reply_kb
                )
        with contextlib.suppress(builtins.BaseException):
            await callback.answer()
    except Exception as e:  # noqa: BLE001
        # 统一使用编辑消息显示错误提示, 并提供关闭按钮
        hint = f"\n\n⚠️ {e!s}"
        close_kb = InlineKeyboardBuilder()
        close_kb.button(text="❌ 关闭", callback_data="quiz:close")
        reply_kb = close_kb.as_markup()
        with contextlib.suppress(builtins.BaseException):
            if callback.message.photo or callback.message.video or callback.message.document:
                original_caption = callback.message.caption or ""
                await callback.message.edit_caption(
                    caption=original_caption + hint,
                    reply_markup=reply_kb
                )
            else:
                original_text = callback.message.text or ""
                await callback.message.edit_text(
                    text=original_text + hint,
                    reply_markup=reply_kb
                )
        with contextlib.suppress(builtins.BaseException):
            await callback.answer()

@router.callback_query(F.data == "quiz:close")
async def on_quiz_close(callback: CallbackQuery) -> None:
    """关闭问答并删除消息

    功能说明:
    - 用户点击“关闭”后, 删除当前题目消息

    输入参数:
    - callback: 回调对象

    返回值:
    - None
    """
    with contextlib.suppress(builtins.BaseException):
        if callback.message:
            await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
    with contextlib.suppress(builtins.BaseException):
        await callback.answer()
