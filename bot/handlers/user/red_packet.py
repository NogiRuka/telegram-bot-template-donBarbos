from __future__ import annotations
from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from bot.core.constants import CURRENCY_NAME
from bot.database.models import RedPacketModel
from bot.services.red_packet_service import RedPacketService

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery
    from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="user_red_packet")


async def _parse_packet_id(data: str | None) -> int | None:
    if not data:
              return None
    prefix = "redpacket:claim:"
    if not data.startswith(prefix):
        return None
    raw_id = data[len(prefix):]
    try:
        return int(raw_id)
    except ValueError:
        return None


async def _update_finished_caption(callback: CallbackQuery, session: AsyncSession, packet_id: int) -> None:
    result = await session.execute(select(RedPacketModel).where(RedPacketModel.id == packet_id))
    packet = result.scalar_one_or_none()
    msg = callback.message
    if not packet or not msg:
        return
    total_amount = int(packet.total_amount)
    taken_count = int(packet.taken_count)
    packet_count = int(packet.packet_count)
    lines: list[str] = []
    lines.append("✅ 红包已被领完")
    lines.append(f"💰 总额：{total_amount} {CURRENCY_NAME}，已全部派发")
    lines.append(f"👥 领取人数：{taken_count} / {packet_count}")
    text = "\n".join(lines)
    try:
        if msg.caption is not None:
            await msg.edit_caption(text, reply_markup=None)
        else:
            await msg.edit_text(text, reply_markup=None)
    except TelegramBadRequest:
        return


async def _update_expired_caption(
    callback: CallbackQuery,
    session: AsyncSession,
    packet_id: int,
    refunded: int,
) -> None:
    result = await session.execute(select(RedPacketModel).where(RedPacketModel.id == packet_id))
    packet = result.scalar_one_or_none()
    msg = callback.message
    if not packet or not msg:
        return
    total_amount = int(packet.total_amount)
    taken_count = int(packet.taken_count)
    packet_count = int(packet.packet_count)
    taken_amount = int(packet.taken_amount)
    lines: list[str] = []
    lines.append("⏰ 红包已过期")
    lines.append(f"💰 总额：{total_amount} {CURRENCY_NAME}，已领取 {taken_amount}")
    lines.append(f"👥 领取人数：{taken_count} / {packet_count}")
    if refunded > 0:
        lines.append(f"↩️ 未领取部分已退款：{refunded} {CURRENCY_NAME}")
    text = "\n".join(lines)
    try:
        if msg.caption is not None:
            await msg.edit_caption(text, reply_markup=None)
        else:
            await msg.edit_text(text, reply_markup=None)
    except TelegramBadRequest:
        return


@router.callback_query(F.data.startswith("redpacket:claim:"))
async def handle_red_packet_claim(callback: CallbackQuery, session: AsyncSession) -> None:
    if not callback.from_user:
        await callback.answer("无法获取用户信息", show_alert=True)
        return
    packet_id = await _parse_packet_id(callback.data)
    if packet_id is None:
        await callback.answer("无效的红包信息", show_alert=True)
        return
    user_id = int(callback.from_user.id)
    chat_id = int(callback.message.chat.id) if callback.message and callback.message.chat else None
    result = await RedPacketService.claim_red_packet(session, packet_id=packet_id, user_id=user_id, chat_id=chat_id)
    success = bool(result.get("success"))
    if not success:
        reason = str(result.get("reason") or "抢红包失败")
        if bool(result.get("expired")):
            refunded = int(result.get("refunded") or 0)
            await _update_expired_caption(callback, session, packet_id, refunded)
        await callback.answer(reason, show_alert=True)
        return
    amount = int(result.get("amount") or 0)
    finished = bool(result.get("finished"))
    await callback.answer(f"🎉 你抢到了 {amount} {CURRENCY_NAME}！", show_alert=True)
    if finished:
        await _update_finished_caption(callback, session, packet_id)
