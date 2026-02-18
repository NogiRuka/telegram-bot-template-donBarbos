from __future__ import annotations
import random
from typing import TYPE_CHECKING, Any

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select

from bot.core.constants import CURRENCY_NAME
from bot.database.models import UserModel
from bot.services.red_packet_cover_service import RedPacketCoverService
from bot.services.red_packet_service import RedPacketService
from bot.utils.permissions import require_user_command_access

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="user_red_packet")

COMMAND_META: dict[str, Any] = {
    "name": "redpacket",
    "alias": "rp",
    "usage": "/rp 金额 [份数或目标用户] [类型] [留言...]",
    "desc": "在群里发红包",
}

DEFAULT_REDPACKET_MESSAGES: list[str] = [
    "新年快乐，大家一起玩～",
    "祝大家天天开心，万事顺意～",
    "来点小惊喜，手速要快哦～",
    "发财发财，一起发财～",
    "冲冲冲，看看今天的手气如何？",
]


def _normalize_message_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    return text


async def _parse_exclusive_by_username(
    session: AsyncSession,
    identifier: str,
) -> int | None:
    username = identifier.removeprefix("@")
    if not username:
        return None
    result = await session.execute(select(UserModel).where(UserModel.username == username))
    user = result.scalar_one_or_none()
    if not user:
        return None
    return int(user.id)


async def _parse_red_packet_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
) -> tuple[int, int, str, int | None, str | None] | tuple[None, None, None, None, None]:
    args_raw = (command.args or "").strip()
    if not args_raw:
        await message.reply("用法: /rp 金额 [份数或目标用户] [类型] [留言...]", parse_mode=None)
        return None, None, None, None, None
    parts = args_raw.split()
    if not parts:
        await message.reply("用法: /rp 金额 [份数或目标用户] [类型] [留言...]", parse_mode=None)
        return None, None, None, None, None
    try:
        total_amount = int(parts[0])
    except ValueError:
        await message.reply("金额必须是正整数", parse_mode=None)
        return None, None, None, None, None
    if total_amount <= 0:
        await message.reply("金额必须大于 0", parse_mode=None)
        return None, None, None, None, None
    reply_to = message.reply_to_message
    if reply_to and reply_to.from_user:
        target_user_id = int(reply_to.from_user.id)
        message_text = _normalize_message_text(" ".join(parts[1:]))
        return total_amount, 1, "exclusive", target_user_id, message_text
    if len(parts) < 2:
        await message.reply("请提供份数或目标用户", parse_mode=None)
        return None, None, None, None, None
    second = parts[1]
    target_user_id: int | None = None
    packet_type = "random"
    packet_count = 1
    message_text: str | None = None
    if second.isdigit():
        value = int(second)
        if value <= 0:
            await message.reply("份数必须大于 0", parse_mode=None)
            return None, None, None, None, None
        if value >= 1_000_000_000:
            target_user_id = value
            packet_type = "exclusive"
            packet_count = 1
            message_text = _normalize_message_text(" ".join(parts[2:]))
            return total_amount, packet_count, packet_type, target_user_id, message_text
        packet_count = value
        if len(parts) >= 3 and parts[2].lower() == "fixed":
            packet_type = "fixed"
            message_text = _normalize_message_text(" ".join(parts[3:]))
        else:
            packet_type = "random"
            message_text = _normalize_message_text(" ".join(parts[2:]))
        return total_amount, packet_count, packet_type, None, message_text
    target_user_id = await _parse_exclusive_by_username(session, second)
    if target_user_id is None:
        await message.reply("未找到目标用户，请确认对方已与机器人有过对话", parse_mode=None)
        return None, None, None, None, None
    packet_type = "exclusive"
    packet_count = 1
    message_text = _normalize_message_text(" ".join(parts[2:]))
    return total_amount, packet_count, packet_type, target_user_id, message_text


@router.message(Command(commands=["rp", "redpacket"]))
@require_user_command_access(COMMAND_META["name"])
async def create_red_packet_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
) -> None:
    if not message.from_user or not message.chat:
        await message.reply("无法获取用户或会话信息", parse_mode=None)
        return
    parsed = await _parse_red_packet_command(message, command, session)
    total_amount, packet_count, packet_type, target_user_id, message_text = parsed
    if total_amount is None or packet_count is None or packet_type is None:
        return
    if not message_text:
        message_text = random.choice(DEFAULT_REDPACKET_MESSAGES)
    try:
        cover_buf, cover_path, cover_template_id = RedPacketCoverService.generate_cover_image(
            user=message.from_user,
            total_amount=total_amount,
            packet_count=packet_count,
            packet_type=packet_type,
            message_text=message_text,
        )
        packet = await RedPacketService.create_red_packet(
            session=session,
            creator_id=int(message.from_user.id),
            chat_id=int(message.chat.id),
            total_amount=total_amount,
            count=packet_count,
            packet_type=packet_type,
            expire_minutes=10,
            target_user_id=target_user_id,
            message_text=message_text,
            cover_template_id=cover_template_id,
        )
    except ValueError as exc:
        await message.reply(str(exc), parse_mode=None)
        return
    except Exception as exc:
        logger.exception(
            "创建红包失败: user_id=%s chat_id=%s total_amount=%s count=%s packet_type=%s",
            message.from_user.id if message.from_user else None,
            message.chat.id if message.chat else None,
            total_amount,
            packet_count,
            packet_type,
        )
        await session.rollback()
        await message.reply("发送红包失败，请稍后重试", parse_mode=None)
        return
    sender_name = message.from_user.full_name or "某人"
    if packet_type == "fixed":
        type_label = "平均分"
    elif packet_type == "exclusive":
        type_label = "专属红包"
    else:
        type_label = "拼手气"
    caption_lines: list[str] = []
    caption_lines.append(f"🧧 {sender_name} 发了一个红包")
    caption_lines.append(f"💰 总额：{total_amount} {CURRENCY_NAME}（{packet_count} 份，{type_label}）")
    caption_lines.append("⏰ 有效期：10 分钟")
    caption_lines.append(f"📝 留言：{message_text}")
    caption = "\n".join(caption_lines)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧧 抢红包",
                    callback_data=f"redpacket:claim:{packet.id}",
                )
            ]
        ]
    )
    try:
        photo_input = FSInputFile(path=str(cover_path))
        sent = await message.answer_photo(photo=photo_input, caption=caption, reply_markup=keyboard)
    except Exception as exc:
        logger.exception(
            "发送红包消息失败: user_id=%s chat_id=%s packet_id=%s cover_path=%s",
            message.from_user.id if message.from_user else None,
            message.chat.id if message.chat else None,
            getattr(packet, "id", None),
            cover_path,
        )
        await session.rollback()
        await message.reply("发送红包消息失败，请稍后重试", parse_mode=None)
        return
    cover_file_id = None
    if sent.photo:
        cover_file_id = sent.photo[-1].file_id
    await RedPacketService.attach_message(
        session=session,
        packet_id=int(packet.id),
        chat_id=int(message.chat.id),
        message_id=int(sent.message_id),
        cover_image_file_id=cover_file_id,
    )
