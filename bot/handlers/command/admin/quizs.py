from __future__ import annotations

import random
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from loguru import logger
from sqlalchemy import select

from bot.config.constants import KEY_ADMIN_QUIZ
from bot.database.models import QuizQuestionModel
from bot.handlers.command.admin._quiz_command import (
    build_usage_text,
    get_random_question_ids,
    is_current_group_admin,
    reply_failure,
    resolve_timeout_sec,
    send_group_quizzes,
)
from bot.utils.permissions import require_admin_command_access, require_admin_feature

if TYPE_CHECKING:
    from aiogram.types import Message
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="command_quiz_multi")

COMMAND_META = {
    "name": "quizs",
    "alias": "qs",
    "usage": "/qs <个数> [时长秒数] [答对奖励] [题目ID列表]",
    "example": {
        "command": "/qs 3 10 10 1-2-3",
        "explain": "发送3条，10秒，答对奖励10，优先使用题目1、2、3",
    },
    "desc": "群管理员在群里批量发送问答",
}


def _parse_question_ids(raw_value: str) -> list[int]:
    parts = [part for part in raw_value.split("-") if part]
    if not parts:
        msg = "题目ID列表不能为空"
        raise ValueError(msg)

    question_ids = [int(part) for part in parts]
    if any(question_id <= 0 for question_id in question_ids):
        msg = "题目ID必须为正整数"
        raise ValueError(msg)
    return question_ids


def _parse_quiz_batch_args(raw_args: str | None) -> tuple[int, int | None, int | None, list[int] | None]:
    if not raw_args:
        msg = "缺少必要参数"
        raise ValueError(msg)

    parts = [part for part in raw_args.split() if part]
    if len(parts) > 4:
        msg = "参数过多"
        raise ValueError(msg)

    count = int(parts[0])
    if count <= 0:
        msg = "个数必须为正整数"
        raise ValueError(msg)

    timeout_sec = int(parts[1]) if len(parts) >= 2 else None
    reward_bonus = int(parts[2]) if len(parts) >= 3 else None
    question_ids = _parse_question_ids(parts[3]) if len(parts) >= 4 else None

    values = [value for value in (timeout_sec, reward_bonus) if value is not None]
    if any(value <= 0 for value in values):
        msg = "参数必须为正整数"
        raise ValueError(msg)

    return count, timeout_sec, reward_bonus, question_ids


async def _resolve_batch_question_ids(
    session: AsyncSession,
    count: int,
    question_ids: list[int] | None,
) -> list[int]:
    if not question_ids:
        return await get_random_question_ids(session, count)

    deduped_ids = list(dict.fromkeys(question_ids))
    stmt = select(QuizQuestionModel.id).where(
        QuizQuestionModel.id.in_(deduped_ids),
        QuizQuestionModel.is_active.is_(True),
    )
    valid_ids = set((await session.execute(stmt)).scalars().all())
    preferred_ids = [question_id for question_id in deduped_ids if question_id in valid_ids]

    if len(preferred_ids) >= count:
        return random.sample(preferred_ids, count)

    remain = count - len(preferred_ids)
    extra_ids = await get_random_question_ids(session, remain, exclude_ids=set(preferred_ids))
    return preferred_ids + extra_ids


@router.message(Command(COMMAND_META["name"], COMMAND_META["alias"]), F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
@require_admin_command_access(COMMAND_META["name"])
@require_admin_feature(KEY_ADMIN_QUIZ)
async def quiz_batch_command(message: Message, command: CommandObject, session: AsyncSession) -> None:
    try:
        if not await is_current_group_admin(message):
            await reply_failure(message, "只有当前群组管理员可以使用这个命令。")
            return

        count, timeout_sec, reward_bonus, question_ids = _parse_quiz_batch_args(command.args)
        effective_timeout = await resolve_timeout_sec(session, timeout_sec)
        if effective_timeout is None:
            await reply_failure(message, "请先配置问答时长，或在命令里传入时长秒数。")
            return

        target_question_ids = await _resolve_batch_question_ids(session, count, question_ids)
        if not target_question_ids:
            await reply_failure(message, "没有可发送的启用题目。")
            return

        sent_count, fail_reasons = await send_group_quizzes(
            message=message,
            session=session,
            question_ids=target_question_ids,
            timeout_sec=effective_timeout,
            reward_bonus=reward_bonus,
        )
        if sent_count == 0:
            reason = fail_reasons[0] if fail_reasons else "问答发送失败"
            await reply_failure(message, reason)
    except ValueError:
        await reply_failure(message, build_usage_text(COMMAND_META), parse_mode="Markdown")
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"群组批量问答命令执行失败: {exc}")
        await reply_failure(message, f"触发失败: {exc}")
