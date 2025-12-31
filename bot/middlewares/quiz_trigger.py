from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from loguru import logger

from bot.services.quiz_service import QuizService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

class QuizTriggerMiddleware(BaseMiddleware):
    """
    问答触发中间件

    在用户与机器人交互后，概率触发问答。
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # 1. 执行原有逻辑
        result = await handler(event, data)

        # 2. 触发检查逻辑
        # 仅针对 Message 和 CallbackQuery
        # 且排除 Quiz 自身的回调 (防止无限套娃)
        user_id = None
        chat_id = None

        if isinstance(event, Message):
            if event.from_user and not event.from_user.is_bot:
                user_id = event.from_user.id
                chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            if event.data and event.data.startswith("quiz:"):
                # 如果是问答相关的点击，不触发新题目
                return result
            if event.from_user and not event.from_user.is_bot:
                user_id = event.from_user.id
                chat_id = event.message.chat.id if event.message else event.from_user.id

        if user_id and chat_id:
            # 获取数据库会话 (假设 DatabaseMiddleware 已注入 session)
            session: AsyncSession = data.get("session")
            bot = data.get("bot")
            if session:
                # 检查触发条件
                if await QuizService.check_trigger_conditions(session, user_id, chat_id, bot):
                    # 创建并发送题目
                    quiz_data = await QuizService.create_quiz_session(session, user_id, chat_id)
                    if quiz_data:
                        question, image, markup, session_id = quiz_data

                        # 发送消息
                        # 尝试获取 bot 实例
                        bot = data.get("bot")
                        if bot:
                            try:
                                sent_msg = None
                                caption = await QuizService.build_quiz_caption(
                                    question=question,
                                    image=image,
                                    session=session
                                )

                                if image:
                                    # 发送图片
                                    # 这里假设 image.file_id 是有效的 Telegram File ID
                                    sent_msg = await bot.send_photo(
                                        chat_id=chat_id,
                                        photo=image.file_id,
                                        caption=caption,
                                        reply_markup=markup
                                    )
                                else:
                                    # 发送文本
                                    sent_msg = await bot.send_message(
                                        chat_id=chat_id,
                                        text=caption,
                                        reply_markup=markup
                                    )

                                if sent_msg:
                                    # 更新 Session 中的 Message ID
                                    await QuizService.update_session_message_id(session, session_id, sent_msg.message_id)

                            except Exception as e:
                                logger.warning(f"⚠️ 发送问答题目失败: {e}")
                                # 发送失败，可能是被屏蔽或者网络问题
                                # 应该回滚/删除 Session 吗？
                                # QuizService.handle_timeout 会处理过期的 Session，这里可以忽略

        return result
