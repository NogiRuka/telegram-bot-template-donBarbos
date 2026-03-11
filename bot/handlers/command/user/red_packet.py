from __future__ import annotations
import asyncio
import io
import secrets
from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from bot.core.constants import CURRENCY_NAME
from bot.database.models import MediaFileModel, UserModel
from bot.services.red_packet_service import RedPacketCreateRequest, RedPacketService
from bot.services.redpacket_preview import compose_redpacket_with_info
from bot.states.user import RedPacketWizardStates
from bot.utils.permissions import require_user_command_access

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="user_red_packet")


COMMAND_META: dict[str, Any] = {
    "name": "redpacket",
    "alias": "rp",
    "usage": "/rp 金额 [份数|@用户名|用户ID] [fixed|exclusive] [留言...]",
    "desc": "在群里发红包",
}

DEFAULT_REDPACKET_MESSAGES: list[str] = [
    "新年快乐，大家一起玩～",
    "祝大家天天开心，万事顺意～",
    "来点小惊喜，手速要快哦～",
    "发财发财，一起发财～",
    "冲冲冲，看看今天的手气如何？",
]

RP_TUTORIAL_PREFIX = "rp:tutorial"
RP_WIZARD_PREFIX = "rp:wizard"

AVATAR_CACHE: dict[str, bytes] = {}

MAX_PACKET_COUNT = 200
MAX_AVATAR_CACHE_SIZE = 100
MIN_ARGS_WITH_SECOND = 2
MIN_ARGS_WITH_TYPE = 3


def _normalize_message_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    return text


def _is_help_trigger(args_raw: str) -> bool:
    if not args_raw.strip():
        return True
    first = args_raw.split(maxsplit=1)[0].strip().lower()
    return first in {"help", "h", "教程", "教學", "指南", "guide", "?", "？"}


def _build_tutorial_text() -> str:
    return "\n".join(
        [
            "🧧 红包功能使用教程",
            "",
            "核心用法（在群里发送）：",
            "1) 拼手气红包：/rp <总额> <份数> [留言...]",
            "2) 平均分红包：/rp <总额> <份数> fixed [留言...]",
            "3) 专属红包：",
            "   - 方式A：回复对方消息后：/rp <总额> [留言...]",
            "   - 方式B：/rp <总额> @用户名 [留言...]",
            "   - 方式C：/rp <总额> <用户ID> exclusive [留言...]",
            "",
            "规则说明：",
            f"- 代币单位：{CURRENCY_NAME}，发红包会先扣除总额，过期未领完会退款",
            "- 有效期：10 分钟",
            "- 专属红包固定 1 份，仅目标用户可领取",
            "",
            "想一步步生成命令：点“生成向导”（建议私聊里用，生成后复制到群）。",
        ]
    )


def _packet_type_label(packet_type: str) -> str:
    if packet_type == "fixed":
        return "平均分"
    if packet_type == "exclusive":
        return "专属红包"
    return "拼手气"


def _build_packet_caption(
    sender_name: str,
    total_amount: int,
    packet_count: int,
    packet_type: str,
    message_text: str,
) -> str:
    type_label = _packet_type_label(packet_type)
    return (
        f"🧧 {sender_name} 发了一个红包\n"
        f"💰 总额：{total_amount} {CURRENCY_NAME}（{packet_count} 份，{type_label}）\n"
        "⏰ 有效期：10 分钟\n"
        f"📝 留言：{message_text}"
    )


def _build_claim_keyboard(packet_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧧 抢红包",
                    callback_data=f"redpacket:claim:{packet_id}",
                )
            ]
        ]
    )


async def _generate_cover_bytes(
    bot: Bot,
    user_id: int,
    sender_name: str,
    total_amount: int,
    packet_count: int,
) -> tuple[bytes, str]:
    avatar_content = await _fetch_user_avatar_bytes(bot, user_id)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: compose_redpacket_with_info(
            cover_name=None,
            body_name=None,
            sender_name=sender_name,
            amount=float(total_amount),
            count=int(packet_count),
            group_text=None,
            watermark_image_name=None,
            avatar_image_name=None,
            avatar_file_content=avatar_content,
            return_bytes=True,
        ),
    )


def _store_cover_media_if_present(session: AsyncSession, sent: Message, filename: str) -> str | None:
    if not sent.photo:
        return None
    p = sent.photo[-1]
    media = MediaFileModel(
        file_id=p.file_id,
        file_unique_id=p.file_unique_id,
        file_size=p.file_size,
        file_name=filename,
        unique_name=filename,
        mime_type="image/webp",
        media_type="photo",
        width=p.width,
        height=p.height,
        description="红包封面图（/rp 命令自动生成）",
    )
    session.add(media)
    return p.file_id


def _build_tutorial_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🧩 生成向导", callback_data=f"{RP_WIZARD_PREFIX}:start"),
                InlineKeyboardButton(text="📌 快速示例", callback_data=f"{RP_TUTORIAL_PREFIX}:examples"),
            ],
            [
                InlineKeyboardButton(text="🎯 专属玩法", callback_data=f"{RP_TUTORIAL_PREFIX}:exclusive"),
                InlineKeyboardButton(text="📋 规则说明", callback_data=f"{RP_TUTORIAL_PREFIX}:rules"),
            ],
        ]
    )


async def _fetch_user_avatar_bytes(bot: Bot, user_id: int) -> bytes | None:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if not photos.photos or not photos.photos[0]:
            return None
        photo = photos.photos[0][-1]
        cache_key = photo.file_unique_id
        cached = AVATAR_CACHE.get(cache_key)
        if cached is not None:
            return cached
        file = await bot.get_file(photo.file_id)
        avatar_io = io.BytesIO()
        await bot.download_file(file.file_path, avatar_io)
        content = avatar_io.getvalue()
        AVATAR_CACHE[cache_key] = content
    except (TelegramAPIError, OSError, RuntimeError, ValueError):
        return None
    else:
        if len(AVATAR_CACHE) > MAX_AVATAR_CACHE_SIZE:
            AVATAR_CACHE.clear()
        return content


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


def _parse_digit_second(
    total_amount: int,
    parts: list[str],
) -> tuple[int, int, str, int | None, str | None] | None:
    value = int(parts[1])
    if value <= 0:
        return None

    if len(parts) >= MIN_ARGS_WITH_TYPE and parts[2].lower() in {"exclusive", "ex"}:
        message_text = _normalize_message_text(" ".join(parts[3:]))
        return total_amount, 1, "exclusive", value, message_text

    if value > MAX_PACKET_COUNT:
        message_text = _normalize_message_text(" ".join(parts[2:]))
        return total_amount, 1, "exclusive", value, message_text

    packet_count = value
    if packet_count > MAX_PACKET_COUNT:
        return None

    packet_type = "fixed" if len(parts) >= MIN_ARGS_WITH_TYPE and parts[2].lower() == "fixed" else "random"
    msg_start = 3 if packet_type == "fixed" else 2
    message_text = _normalize_message_text(" ".join(parts[msg_start:]))
    return total_amount, packet_count, packet_type, None, message_text


async def _parse_username_second(
    message: Message,
    total_amount: int,
    session: AsyncSession,
    identifier: str,
    rest_parts: list[str],
) -> tuple[int, int, str, int | None, str | None] | None:
    target_user_id = await _parse_exclusive_by_username(session, identifier)
    if target_user_id is None:
        await message.reply("未找到目标用户，请确认对方已与机器人有过对话", parse_mode=None)
        return None
    message_text = _normalize_message_text(" ".join(rest_parts))
    return total_amount, 1, "exclusive", target_user_id, message_text


async def _parse_red_packet_command(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
) -> tuple[int, int, str, int | None, str | None] | None:
    args_raw = (command.args or "").strip()
    error: str | None = None
    if not args_raw:
        error = "用法: /rp 金额 [份数或目标用户] [类型] [留言...]"
    else:
        parts = args_raw.split()
        try:
            total_amount = int(parts[0])
        except ValueError:
            error = "金额必须是正整数"
        else:
            if total_amount <= 0:
                error = "金额必须大于 0"
    if error is not None:
        await message.reply(error, parse_mode=None)
        return None

    reply_to = message.reply_to_message
    if reply_to and reply_to.from_user:
        target_user_id = int(reply_to.from_user.id)
        message_text = _normalize_message_text(" ".join(parts[1:]))
        return total_amount, 1, "exclusive", target_user_id, message_text
    if len(parts) < MIN_ARGS_WITH_SECOND:
        await message.reply("请提供份数或目标用户", parse_mode=None)
        return None
    second = parts[1]
    if second.isdigit():
        parsed = _parse_digit_second(total_amount, parts)
        if parsed is None:
            await message.reply("参数不合法，请检查金额/份数/类型", parse_mode=None)
            return None
        return parsed
    return await _parse_username_second(message, total_amount, session, second, parts[2:])


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
    args_raw = (command.args or "").strip()
    if _is_help_trigger(args_raw):
        await message.reply(_build_tutorial_text(), reply_markup=_build_tutorial_keyboard(), parse_mode=None)
        return
    if message.chat.type not in {"group", "supergroup"}:
        await message.reply("请在群里发送红包；私聊里可用 /rp 教程 或点“生成向导”生成命令。", parse_mode=None)
        return
    await _create_and_send_red_packet(message, command, session)


async def _create_and_send_red_packet(message: Message, command: CommandObject, session: AsyncSession) -> None:
    parsed = await _parse_red_packet_command(message, command, session)
    if parsed is None:
        return
    total_amount, packet_count, packet_type, target_user_id, message_text = parsed
    if not message_text:
        message_text = secrets.choice(DEFAULT_REDPACKET_MESSAGES)
    try:
        sender_name = message.from_user.full_name or "某人"
        cover_bytes, filename = await _generate_cover_bytes(
            bot=message.bot,
            user_id=int(message.from_user.id),
            sender_name=sender_name,
            total_amount=total_amount,
            packet_count=packet_count,
        )
    except (OSError, RuntimeError, ValueError):
        logger.exception(
            "生成红包封面失败: user_id=%s chat_id=%s total_amount=%s count=%s packet_type=%s",
            message.from_user.id,
            message.chat.id,
            total_amount,
            packet_count,
            packet_type,
        )
        await message.reply("生成红包封面失败，请稍后重试", parse_mode=None)
        return

    try:
        req = RedPacketCreateRequest(
            creator_id=int(message.from_user.id),
            chat_id=int(message.chat.id),
            total_amount=total_amount,
            count=packet_count,
            packet_type=packet_type,
            expire_minutes=10,
            target_user_id=target_user_id,
            message_text=message_text,
            cover_template_id=None,
        )
        packet = await RedPacketService.create_red_packet(session=session, req=req)
    except (ValueError, SQLAlchemyError) as exc:
        await session.rollback()
        await message.reply(str(exc), parse_mode=None)
        return

    caption = _build_packet_caption(sender_name, total_amount, packet_count, packet_type, message_text)
    keyboard = _build_claim_keyboard(int(packet.id))
    try:
        photo_input = BufferedInputFile(cover_bytes, filename=filename)
        sent = await message.answer_photo(photo=photo_input, caption=caption, reply_markup=keyboard, parse_mode=None)
    except TelegramAPIError:
        await session.rollback()
        await message.reply("发送红包消息失败，请稍后重试", parse_mode=None)
        return

    cover_file_id = _store_cover_media_if_present(session, sent, filename)
    await RedPacketService.attach_message(
        session=session,
        packet_id=int(packet.id),
        chat_id=int(message.chat.id),
        message_id=int(sent.message_id),
        cover_image_file_id=cover_file_id,
    )


@router.callback_query(F.data == f"{RP_TUTORIAL_PREFIX}:examples")
async def rp_tutorial_examples(callback: CallbackQuery) -> None:
    text = (
        "📌 快速示例\n\n"
        "拼手气：\n"
        "/rp 100 10 恭喜发财\n\n"
        "平均分：\n"
        "/rp 100 10 fixed 平分好运\n\n"
        "专属（方式A：回复对方消息）：\n"
        "回复某人后发送：/rp 66 给你的小惊喜\n\n"
        "专属（方式B：@用户名）：\n"
        "/rp 66 @someone 给你的小惊喜\n\n"
        "专属（方式C：用户ID）：\n"
        "/rp 66 123456789 exclusive 给你的小惊喜"
    )
    await callback.answer()
    if callback.message:
        await callback.message.reply(text, parse_mode=None)


@router.callback_query(F.data == f"{RP_TUTORIAL_PREFIX}:exclusive")
async def rp_tutorial_exclusive(callback: CallbackQuery) -> None:
    text = (
        "🎯 专属红包玩法\n\n"
        "1) 最简单：在群里“回复对方消息”，再发：\n"
        "/rp <总额> [留言...]\n\n"
        "2) 也可以用 @用户名：\n"
        "/rp <总额> @用户名 [留言...]\n\n"
        "3) 或直接填用户ID：\n"
        "/rp <总额> <用户ID> exclusive [留言...]\n\n"
        "提示：如果用 @用户名 找不到，多半是对方没和机器人对话过。"
    )
    await callback.answer()
    if callback.message:
        await callback.message.reply(text, parse_mode=None)


@router.callback_query(F.data == f"{RP_TUTORIAL_PREFIX}:rules")
async def rp_tutorial_rules(callback: CallbackQuery) -> None:
    text = "\n".join(
        [
            "📋 规则说明",
            "",
            f"- 发红包会先扣除总额（单位：{CURRENCY_NAME}）",
            "- 有效期 10 分钟；过期未领完会自动退款给发红包的人",
            "- 专属红包固定 1 份，只有目标用户能抢",
            "- 每个人同一个红包只能抢一次",
        ]
    )
    await callback.answer()
    if callback.message:
        await callback.message.reply(text, parse_mode=None)


def _wizard_keyboard_types() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎲 拼手气", callback_data=f"{RP_WIZARD_PREFIX}:type:random"),
                InlineKeyboardButton(text="📏 平均分", callback_data=f"{RP_WIZARD_PREFIX}:type:fixed"),
            ],
            [InlineKeyboardButton(text="🎯 专属", callback_data=f"{RP_WIZARD_PREFIX}:type:exclusive")],
            [InlineKeyboardButton(text="退出", callback_data=f"{RP_WIZARD_PREFIX}:cancel")],
        ]
    )


def _wizard_keyboard_finish() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🖼️ 预览封面", callback_data=f"{RP_WIZARD_PREFIX}:preview"),
                InlineKeyboardButton(text="🔁 重新开始", callback_data=f"{RP_WIZARD_PREFIX}:restart"),
            ],
            [InlineKeyboardButton(text="退出", callback_data=f"{RP_WIZARD_PREFIX}:cancel")],
        ]
    )


@router.callback_query(F.data == f"{RP_WIZARD_PREFIX}:start")
async def rp_wizard_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.from_user:
        return
    chat_type = callback.message.chat.type if callback.message and callback.message.chat else None
    if chat_type != "private":
        text = "建议在私聊里用向导：私聊我后发送 /rp 教程，然后点“生成向导”。"
        if callback.message:
            await callback.message.reply(text, parse_mode=None)
        return
    await state.clear()
    await state.set_state(RedPacketWizardStates.waiting_for_type)
    await state.update_data(wizard_user_id=int(callback.from_user.id))
    if callback.message:
        await callback.message.reply("请选择红包类型：", reply_markup=_wizard_keyboard_types(), parse_mode=None)


@router.callback_query(F.data.startswith(f"{RP_WIZARD_PREFIX}:type:"))
async def rp_wizard_choose_type(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.from_user:
        return
    data = await state.get_data()
    if int(data.get("wizard_user_id") or 0) != int(callback.from_user.id):
        return
    prefix = f"{RP_WIZARD_PREFIX}:type:"
    packet_type = (callback.data or "")[len(prefix):]
    if packet_type not in {"random", "fixed", "exclusive"}:
        return
    await state.update_data(packet_type=packet_type)
    await state.set_state(RedPacketWizardStates.waiting_for_amount)
    if callback.message:
        await callback.message.reply(f"请输入红包总金额（正整数，单位：{CURRENCY_NAME}）：", parse_mode=None)


@router.callback_query(F.data == f"{RP_WIZARD_PREFIX}:restart")
async def rp_wizard_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.from_user:
        return
    await state.clear()
    await state.set_state(RedPacketWizardStates.waiting_for_type)
    await state.update_data(wizard_user_id=int(callback.from_user.id))
    if callback.message:
        await callback.message.reply("请选择红包类型：", reply_markup=_wizard_keyboard_types(), parse_mode=None)


@router.callback_query(F.data == f"{RP_WIZARD_PREFIX}:cancel")
async def rp_wizard_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if callback.message:
        await callback.message.reply("已退出红包向导。", parse_mode=None)


@router.message(StateFilter(RedPacketWizardStates.waiting_for_amount))
async def rp_wizard_amount(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    if int(data.get("wizard_user_id") or 0) != int(message.from_user.id):
        return
    text = (message.text or "").strip()
    if text in {"/cancel", "取消"}:
        await state.clear()
        await message.reply("已退出红包向导。", parse_mode=None)
        return
    try:
        amount = int(text)
    except ValueError:
        await message.reply("请输入正整数金额。", parse_mode=None)
        return
    if amount <= 0:
        await message.reply("金额必须大于 0。", parse_mode=None)
        return
    await state.update_data(total_amount=amount)
    packet_type = str(data.get("packet_type") or "random")
    if packet_type == "exclusive":
        await state.set_state(RedPacketWizardStates.waiting_for_target)
        await message.reply("请输入目标用户（@用户名 或 用户ID）。", parse_mode=None)
        return
    await state.set_state(RedPacketWizardStates.waiting_for_count)
    await message.reply(f"请输入红包份数（正整数，建议不超过 {MAX_PACKET_COUNT}）。", parse_mode=None)


@router.message(StateFilter(RedPacketWizardStates.waiting_for_count))
async def rp_wizard_count(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    if int(data.get("wizard_user_id") or 0) != int(message.from_user.id):
        return
    text = (message.text or "").strip()
    if text in {"/cancel", "取消"}:
        await state.clear()
        await message.reply("已退出红包向导。", parse_mode=None)
        return
    try:
        count = int(text)
    except ValueError:
        await message.reply("请输入正整数份数。", parse_mode=None)
        return
    if count <= 0:
        await message.reply("份数必须大于 0。", parse_mode=None)
        return
    if count > MAX_PACKET_COUNT:
        await message.reply(f"份数过大，建议不超过 {MAX_PACKET_COUNT}。", parse_mode=None)
        return
    await state.update_data(packet_count=count)
    await state.set_state(RedPacketWizardStates.waiting_for_message)
    await message.reply("请输入红包留言（可空，直接发送“.” 表示随机一句）：", parse_mode=None)


@router.message(StateFilter(RedPacketWizardStates.waiting_for_target))
async def rp_wizard_target(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    if int(data.get("wizard_user_id") or 0) != int(message.from_user.id):
        return
    text = (message.text or "").strip()
    if text in {"/cancel", "取消"}:
        await state.clear()
        await message.reply("已退出红包向导。", parse_mode=None)
        return
    target_user_id: int | None = None
    if text.isdigit():
        try:
            target_user_id = int(text)
        except ValueError:
            target_user_id = None
    else:
        target_user_id = await _parse_exclusive_by_username(session, text)
    if target_user_id is None:
        await message.reply("未找到目标用户，请改用用户ID，或确认对方已与机器人对话过。", parse_mode=None)
        return
    await state.update_data(target_user_id=target_user_id, packet_count=1)
    await state.set_state(RedPacketWizardStates.waiting_for_message)
    await message.reply("请输入红包留言（可空，直接发送“.” 表示随机一句）：", parse_mode=None)


@router.message(StateFilter(RedPacketWizardStates.waiting_for_message))
async def rp_wizard_message(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    data = await state.get_data()
    if int(data.get("wizard_user_id") or 0) != int(message.from_user.id):
        return
    raw = (message.text or "").strip()
    if raw in {"/cancel", "取消"}:
        await state.clear()
        await message.reply("已退出红包向导。", parse_mode=None)
        return
    msg_text = None
    if raw and raw != ".":
        msg_text = raw
    await state.update_data(message_text=msg_text)
    total_amount = int(data.get("total_amount") or 0)
    packet_count = int(data.get("packet_count") or 1)
    packet_type = str(data.get("packet_type") or "random")
    target_user_id = data.get("target_user_id")
    if packet_type == "exclusive":
        if isinstance(target_user_id, int):
            cmd = f"/rp {total_amount} {target_user_id}"
            if target_user_id <= MAX_PACKET_COUNT:
                cmd += " exclusive"
        else:
            cmd = f"/rp {total_amount}"
    else:
        cmd = f"/rp {total_amount} {packet_count}"
        if packet_type == "fixed":
            cmd += " fixed"
    if msg_text:
        cmd += f" {msg_text}"
    hint = f"✅ 已生成命令（复制到目标群发送即可）：\n{cmd}\n\n可选：点“预览封面”看看效果（不会真的扣款/发红包）。"
    await message.reply(hint, reply_markup=_wizard_keyboard_finish(), parse_mode=None)


@router.callback_query(F.data == f"{RP_WIZARD_PREFIX}:preview")
async def rp_wizard_preview(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.from_user or not callback.message:
        return
    data = await state.get_data()
    if int(data.get("wizard_user_id") or 0) != int(callback.from_user.id):
        return
    total_amount = int(data.get("total_amount") or 0)
    packet_count = int(data.get("packet_count") or 1)
    if total_amount <= 0:
        await callback.message.reply("向导数据不完整，请重新开始。", parse_mode=None)
        return
    avatar_content = await _fetch_user_avatar_bytes(callback.bot, int(callback.from_user.id))
    sender_name = callback.from_user.full_name or "某人"
    loop = asyncio.get_running_loop()
    cover_bytes, filename = await loop.run_in_executor(
        None,
        lambda: compose_redpacket_with_info(
            cover_name=None,
            body_name=None,
            sender_name=sender_name,
            amount=float(total_amount),
            count=int(packet_count),
            group_text=None,
            watermark_image_name=None,
            avatar_image_name=None,
            avatar_file_content=avatar_content,
            return_bytes=True,
        ),
    )
    photo_input = BufferedInputFile(cover_bytes, filename=filename)
    await callback.message.reply_photo(photo=photo_input, caption="🧧 红包封面预览", parse_mode=None)
