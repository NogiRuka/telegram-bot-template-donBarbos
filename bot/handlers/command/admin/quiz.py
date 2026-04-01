from __future__ import annotations
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from loguru import logger
from sqlalchemy import func, select

from bot.config.constants import KEY_ADMIN_QUIZ, KEY_QUIZ_SESSION_TIMEOUT
from bot.database.models import QuizQuestionModel
from bot.services.config_service import get_config
from bot.services.quiz_service import QuizService
from bot.utils.message import delete_message_after_delay, safe_delete_message
from bot.utils.permissions import require_admin_command_access, require_admin_feature

if TYPE_CHECKING:
    from aiogram.types import Message
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="command_quiz")

COMMAND_NAME = "quiz"
COMMAND_ALIAS = "q"
AUTO_DELETE_SECONDS = 10

COMMAND_META = {
    "name": COMMAND_NAME,
    "alias": COMMAND_ALIAS,
    "usage": {
        "summary": "/q <个数> [题目ID] [时长秒数] [答对奖励]",
        "formats": [
            "/q 1",
            "/q 1 12",
            "/q 1 12 30",
            "/q 1 12 30 30",
        ],
        "examples": [
            "/q 1 随机发送 1 条问答",
            "/q 1 12 指定第 12 题",
            "/q 1 12 30 指定第 12 题，限时 30 秒",
            "/q 1 12 30 30 指定第 12 题，限时 30 秒，答对奖励 30",
        ],
    },
    "desc": "桜之问答，启动！",
}


async def _is_current_group_admin(message: Message) -> bool:
    if not message.from_user:
        return False

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR)


def _parse_quiz_args(raw_args: str | None) -> tuple[int, int | None, int | None, int | None]:
    if not raw_args:
        msg = "missing args"
        raise ValueError(msg)

    parts = [part for part in raw_args.split() if part]
    if len(parts) > 4:
        msg = "too many args"
        raise ValueError(msg)

    values = [int(part) for part in parts]
    count = values[0]
    if count <= 0:
        msg = "count must be positive"
        raise ValueError(msg)

    question_id = values[1] if len(values) >= 2 else None
    timeout_sec = values[2] if len(values) >= 3 else None
    reward_bonus = values[3] if len(values) >= 4 else None
    return count, question_id, timeout_sec, reward_bonus


def _usage_text() -> str:
    usage = COMMAND_META.get("usage")
    if not isinstance(usage, dict):
        msg = "invalid usage meta"
        raise TypeError(msg)
    summary = str(usage.get("summary") or "")
    raw_formats = usage.get("formats", [])
    raw_examples = usage.get("examples", [])

    if not isinstance(raw_formats, (list, tuple)):
        raw_formats = [raw_formats] if raw_formats else []
    if not isinstance(raw_examples, (list, tuple)):
        raw_examples = [raw_examples] if raw_examples else []

    format_lines = [str(it) for it in raw_formats]
    example_lines = [str(it) for it in raw_examples]

    format_text = "\n".join([f"`{line}`" for line in format_lines])
    example_text = "\n".join([f"`{line}`" for line in example_lines])
    return (
        f"{COMMAND_META['desc']}\n\n"
        f"总格式:\n`{summary}`\n\n"
        "用法:\n"
        f"{format_text}\n\n"
        "示例说明:\n"
        f"{example_text}"
    )


async def _reply_failure(message: Message, text: str, parse_mode: str | None = None) -> None:
    sent = await message.reply(text, parse_mode=parse_mode)
    delete_message_after_delay(sent, delay=AUTO_DELETE_SECONDS)
    delete_message_after_delay(message, delay=AUTO_DELETE_SECONDS)


async def _resolve_question_ids(
    session: AsyncSession,
    count: int,
    question_id: int | None,
) -> list[int]:
    if question_id is not None:
        return [question_id]
    stmt = (
        select(QuizQuestionModel.id)
        .where(QuizQuestionModel.is_active.is_(True))
        .order_by(func.random())
        .limit(count)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [int(row) for row in rows]


@router.message(Command(COMMAND_NAME, COMMAND_ALIAS), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
@require_admin_command_access(COMMAND_NAME)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def quiz_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    try:
        if not await _is_current_group_admin(message):
            await _reply_failure(message, "只有当前群组管理员可以使用这个命令。")
            return

        if not command.args:
            await _reply_failure(message, _usage_text(), parse_mode="Markdown")
            return

        count, question_id, timeout_sec, reward_bonus = _parse_quiz_args(command.args)

        if question_id is not None:
            stmt = select(QuizQuestionModel).where(
                QuizQuestionModel.id == question_id,
                QuizQuestionModel.is_active.is_(True),
            )
            question = (await session.execute(stmt)).scalar_one_or_none()
            if not question:
                await _reply_failure(message, f"题目 `{question_id}` 不存在或未启用。", parse_mode="Markdown")
                return

        effective_timeout = timeout_sec
        if effective_timeout is None:
            effective_timeout = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
            if effective_timeout is None:
                await _reply_failure(message, "请提供时长秒数，或先配置问答时长。")
                return

        target_question_ids = await _resolve_question_ids(session, count, question_id)
        if not target_question_ids:
            await _reply_failure(message, "没有可发送的启用题目。")
            return

        sent_count = 0
        fail_reasons: list[str] = []

        for target_question_id in target_question_ids:
            try:
                quiz_owner_id = QuizService.build_group_session_user_id(message.chat.id)
                quiz_data = await QuizService.create_quiz_session(
                    session,
                    quiz_owner_id,
                    message.chat.id,
                    allow_parallel=True,
                    question_id=target_question_id,
                    timeout_sec=effective_timeout,
                    reward_bonus=reward_bonus,
                    title="桜之问答",
                )
            except Exception as e:  # noqa: BLE001
                fail_reasons.append(f"创建问答会话失败: {e}")
                continue

            if not quiz_data:
                fail_reasons.append("创建问答会话失败：未返回会话数据。")
                continue

            question, image, markup, session_id = quiz_data
            caption = await QuizService.build_quiz_caption(
                question=question,
                image=image,
                session=session,
                timeout_sec=effective_timeout,
                title="桜之问答",
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
            except Exception as e:  # noqa: BLE001
                fail_reasons.append(f"发送题目失败(题目ID={question.id}): {e}")
                await QuizService.handle_timeout_by_session_id(session, session_id)
                continue

            await QuizService.update_session_message_id(session, session_id, sent.message_id)
            QuizService.start_timeout_task(
                bot=message.bot,
                chat_id=message.chat.id,
                message_id=sent.message_id,
                session_id=session_id,
                timeout=int(effective_timeout),
            )
            sent_count += 1

        if sent_count == 0:
            reason = fail_reasons[0]
            await _reply_failure(message, f"问答发送失败：{reason}")
            return

        await safe_delete_message(message.bot, message.chat.id, message.message_id)
    except ValueError:
        await _reply_failure(message, _usage_text(), parse_mode="Markdown")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"群组问答命令执行失败: {e}")
        await _reply_failure(message, f"触发失败: {e}")
