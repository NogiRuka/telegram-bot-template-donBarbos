from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.enums import ChatMemberStatus
from loguru import logger
from sqlalchemy import select

from bot.database.models import QuizQuestionModel
from bot.handlers.command._usage import build_usage_text

from bot.config.constants import KEY_QUIZ_SESSION_TIMEOUT
from bot.services.config_service import get_config
from bot.services.quiz_service import QuizService
from bot.utils.message import delete_message_after_delay, safe_delete_message

if TYPE_CHECKING:
    from aiogram.types import Message
    from sqlalchemy.ext.asyncio import AsyncSession

AUTO_DELETE_SECONDS = 10
QUIZ_TITLE = "桜之问答"


async def reply_failure(message: Message, text: str, parse_mode: str | None = None) -> None:
    sent = await message.reply(text, parse_mode=parse_mode)
    delete_message_after_delay(sent, delay=AUTO_DELETE_SECONDS)
    delete_message_after_delay(message, delay=AUTO_DELETE_SECONDS)


async def is_current_group_admin(message: Message) -> bool:
    if not message.from_user:
        return False

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)


async def resolve_timeout_sec(session: AsyncSession, timeout_sec: int | None) -> int | None:
    if timeout_sec is not None:
        return timeout_sec
    config_timeout = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
    if config_timeout is None:
        return None
    return int(config_timeout)


async def get_random_question_ids(
    session: AsyncSession,
    count: int,
    *,
    exclude_ids: set[int] | None = None,
) -> list[int]:
    stmt = select(QuizQuestionModel.id).where(QuizQuestionModel.is_active.is_(True))
    if exclude_ids:
        stmt = stmt.where(QuizQuestionModel.id.not_in(exclude_ids))
    stmt = stmt.order_by(QuizQuestionModel.id.desc())

    question_ids = list((await session.execute(stmt)).scalars().all())
    if not question_ids:
        return []

    import random

    if len(question_ids) <= count:
        random.shuffle(question_ids)
        return question_ids

    return random.sample(question_ids, count)


async def send_group_quizzes(
    *,
    message: Message,
    session: AsyncSession,
    question_ids: list[int],
    timeout_sec: int,
    reward_bonus: int | None,
) -> tuple[int, list[str]]:
    sent_count = 0
    fail_reasons: list[str] = []
    quiz_owner_id = QuizService.build_group_session_user_id(message.chat.id)

    for question_id in question_ids:
        try:
            quiz_data = await QuizService.create_quiz_session(
                session,
                quiz_owner_id,
                message.chat.id,
                allow_parallel=True,
                question_id=question_id,
                timeout_sec=timeout_sec,
                reward_bonus=reward_bonus,
                title=QUIZ_TITLE,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"创建群组问答会话失败，题目ID={question_id}: {exc}")
            fail_reasons.append(f"创建题目 {question_id} 失败: {exc}")
            continue

        if not quiz_data:
            fail_reasons.append(f"题目 {question_id} 创建失败")
            continue

        question, image, markup, session_id = quiz_data
        caption = await QuizService.build_quiz_caption(
            question=question,
            image=image,
            session=session,
            timeout_sec=timeout_sec,
            title=QUIZ_TITLE,
        )

        try:
            if image:
                sent = await message.bot.send_photo(
                    chat_id=message.chat.id,
                    photo=image.file_id,
                    caption=caption,
                    reply_markup=markup,
                )
            else:
                sent = await message.bot.send_message(
                    chat_id=message.chat.id,
                    text=caption,
                    reply_markup=markup,
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"发送群组问答失败，题目ID={question.id}: {exc}")
            fail_reasons.append(f"发送题目 {question.id} 失败: {exc}")
            await QuizService.handle_timeout_by_session_id(session, session_id)
            continue

        await QuizService.update_session_message_id(session, session_id, sent.message_id)
        QuizService.start_timeout_task(
            bot=message.bot,
            chat_id=message.chat.id,
            message_id=sent.message_id,
            session_id=session_id,
            timeout=timeout_sec,
        )
        sent_count += 1

    if sent_count > 0:
        await safe_delete_message(message.bot, message.chat.id, message.message_id)

    return sent_count, fail_reasons
