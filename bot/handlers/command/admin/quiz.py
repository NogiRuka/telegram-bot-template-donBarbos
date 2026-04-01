from __future__ import annotations
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import Command, CommandObject
from loguru import logger
from sqlalchemy import select

from bot.config.constants import KEY_ADMIN_QUIZ, KEY_QUIZ_SESSION_TIMEOUT
from bot.database.models import QuizQuestionModel
from bot.services.config_service import get_config
from bot.services.quiz_service import QuizService
from bot.utils.permissions import require_admin_command_access, require_admin_feature

if TYPE_CHECKING:
    from aiogram.types import Message
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="command_quiz")

COMMAND_NAME = "quiz"
COMMAND_ALIAS = "q"

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
    summary = ""
    formats: list[str] = []
    examples: list[str] = []

    if isinstance(usage, dict):
        summary = str(usage.get("summary") or "")
        raw_formats = usage.get("formats") or []
        raw_examples = usage.get("examples") or []
        if isinstance(raw_formats, (list, tuple)):
            formats = [str(it) for it in raw_formats if str(it).strip()]
        elif isinstance(raw_formats, str) and raw_formats.strip():
            formats = [raw_formats]
        if isinstance(raw_examples, (list, tuple)):
            examples = [str(it) for it in raw_examples if str(it).strip()]
        elif isinstance(raw_examples, str) and raw_examples.strip():
            examples = [raw_examples]
    else:
        summary = str(usage or "")

    format_lines = formats if formats else ["/q 1", "/q 1 12", "/q 1 12 30", "/q 1 12 30 30"]
    example_lines = (
        examples
        if examples
        else [
            "/q 1 随机发送 1 条问答",
            "/q 1 12 指定第 12 题",
            "/q 1 12 30 指定第 12 题，限时 30 秒",
            "/q 1 12 30 30 指定第 12 题，限时 30 秒，答对奖励 30",
        ]
    )

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


@router.message(Command(COMMAND_NAME, COMMAND_ALIAS), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
@require_admin_command_access(COMMAND_NAME)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def quiz_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    try:
        if not await _is_current_group_admin(message):
            await message.reply("只有当前群组管理员可以使用这个命令。")
            return

        if not command.args:
            await message.reply(_usage_text(), parse_mode="Markdown")
            return

        count, question_id, timeout_sec, reward_bonus = _parse_quiz_args(command.args)

        if question_id is not None:
            stmt = select(QuizQuestionModel).where(
                QuizQuestionModel.id == question_id,
                QuizQuestionModel.is_active.is_(True),
            )
            question = (await session.execute(stmt)).scalar_one_or_none()
            if not question:
                await message.reply(f"题目 `{question_id}` 不存在或未启用。", parse_mode="Markdown")
                return

        effective_timeout = timeout_sec
        if effective_timeout is None:
            effective_timeout = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)
            if effective_timeout is None:
                effective_timeout = 60

        sent_count = 0
        sent_ids: list[int] = []

        for _ in range(count):
            quiz_owner_id = QuizService.build_group_session_user_id(message.chat.id)
            quiz_data = await QuizService.create_quiz_session(
                session,
                quiz_owner_id,
                message.chat.id,
                allow_parallel=True,
                question_id=question_id,
                timeout_sec=effective_timeout,
                reward_bonus=reward_bonus,
                title="群组问答",
            )
            if not quiz_data:
                continue

            question, image, markup, session_id = quiz_data
            caption = await QuizService.build_quiz_caption(
                question=question,
                image=image,
                session=session,
                timeout_sec=effective_timeout,
                title="群组问答",
            )

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

            await QuizService.update_session_message_id(session, session_id, sent.message_id)
            QuizService.start_timeout_task(
                bot=message.bot,
                chat_id=message.chat.id,
                message_id=sent.message_id,
                session_id=session_id,
                timeout=int(effective_timeout),
            )
            sent_count += 1
            sent_ids.append(question.id)

        if sent_count == 0:
            await message.reply("问答发送失败，题库可能不可用。")
            return

        summary = [f"已发送 {sent_count} 条问答", f"题目ID: {', '.join(map(str, sent_ids))}", f"{effective_timeout} 秒"]
        if reward_bonus is not None:
            summary.append(f"答对奖励 {reward_bonus}")
        await message.reply(" | ".join(summary))
    except ValueError:
        await message.reply(_usage_text(), parse_mode="Markdown")
    except Exception as e:  # noqa: BLE001
        logger.exception(f"群组问答命令执行失败: {e}")
        await message.reply(f"触发失败: {e}")
