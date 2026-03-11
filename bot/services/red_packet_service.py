from __future__ import annotations
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select, update

from bot.database.models import RedPacketClaimModel, RedPacketModel
from bot.services.currency import CurrencyService
from bot.utils.datetime import now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class RedPacketCreateRequest:
    creator_id: int
    chat_id: int
    total_amount: int
    count: int
    packet_type: str
    expire_minutes: int
    target_user_id: int | None = None
    message_text: str | None = None
    cover_template_id: int | None = None


class RedPacketService:
    @staticmethod
    async def create_red_packet(
        session: AsyncSession,
        req: RedPacketCreateRequest,
    ) -> RedPacketModel:
        if req.total_amount <= 0:
            msg = "⚠️ 红包总金额必须大于 0"
            raise ValueError(msg)
        if req.count <= 0:
            msg = "⚠️ 红包份数必须大于 0"
            raise ValueError(msg)
        if req.total_amount < req.count and req.packet_type != "exclusive":
            msg = "⚠️ 非专属红包总金额必须大于等于份数"
            raise ValueError(msg)
        count = 1 if req.packet_type == "exclusive" else req.count
        expire_at = now() + timedelta(minutes=req.expire_minutes)
        await CurrencyService.add_currency(
            session=session,
            user_id=req.creator_id,
            amount=-req.total_amount,
            event_type="red_packet_create",
            description=f"发红包，金额 {req.total_amount}",
            meta={
                "chat_id": req.chat_id,
                "packet_type": req.packet_type,
            },
            is_consumed=True,
            commit=False,
        )
        packet = RedPacketModel(
            chat_id=req.chat_id,
            message_id=None,
            creator_user_id=req.creator_id,
            total_amount=req.total_amount,
            packet_count=count,
            packet_type=req.packet_type,
            target_user_id=req.target_user_id,
            taken_count=0,
            taken_amount=0,
            status="active",
            expire_at=expire_at,
            cover_template_id=req.cover_template_id,
            cover_image_file_id=None,
            message_text=req.message_text,
        )
        session.add(packet)
        await session.flush()
        return packet

    @staticmethod
    async def attach_message(
        session: AsyncSession,
        packet_id: int,
        chat_id: int,
        message_id: int,
        cover_image_file_id: str | None,
    ) -> None:
        stmt = (
            update(RedPacketModel)
            .where(
                RedPacketModel.id == packet_id,
                RedPacketModel.chat_id == chat_id,
            )
            .values(message_id=message_id, cover_image_file_id=cover_image_file_id)
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    def _random_amount(remaining: int, remain_count: int) -> int:
        if remain_count <= 1:
            return remaining
        min_amount = 1
        max_amount = remaining - (remain_count - 1) * min_amount
        if max_amount <= min_amount:
            return min_amount
        upper = max(min_amount, max_amount // 2)
        return min_amount + secrets.randbelow(upper - min_amount + 1)

    @staticmethod
    def _compute_claim_amount(packet: RedPacketModel) -> int | None:
        remaining_count = int(packet.packet_count) - int(packet.taken_count)
        remaining_amount = int(packet.total_amount) - int(packet.taken_amount)
        if remaining_count <= 0 or remaining_amount <= 0:
            return None
        if packet.packet_type == "fixed":
            if remaining_count == 1:
                return remaining_amount
            return int(packet.total_amount) // int(packet.packet_count)
        return RedPacketService._random_amount(remaining_amount, remaining_count)

    @staticmethod
    async def _claim_active_packet(session: AsyncSession, packet: RedPacketModel, user_id: int) -> dict[str, Any]:
        claim_check_stmt = select(RedPacketClaimModel).where(
            and_(RedPacketClaimModel.packet_id == packet.id, RedPacketClaimModel.user_id == user_id)
        )
        claim_check_res = await session.execute(claim_check_stmt)
        existed = claim_check_res.scalar_one_or_none()
        if existed:
            return {"success": False, "reason": "你已经抢过这个红包了"}

        amount = RedPacketService._compute_claim_amount(packet)
        if amount is None:
            return {"success": False, "reason": "红包已经被抢完啦"}

        new_taken_count = int(packet.taken_count) + 1
        new_taken_amount = int(packet.taken_amount) + int(amount)
        if new_taken_count > int(packet.packet_count) or new_taken_amount > int(packet.total_amount):
            return {"success": False, "reason": "红包已经被抢完啦"}

        claim = RedPacketClaimModel(packet_id=packet.id, user_id=user_id, amount=amount, is_rolled_back=False)
        session.add(claim)
        packet.taken_count = new_taken_count
        packet.taken_amount = new_taken_amount
        if packet.taken_count >= packet.packet_count or packet.taken_amount >= packet.total_amount:
            packet.status = "finished"

        await CurrencyService.add_currency(
            session=session,
            user_id=user_id,
            amount=amount,
            event_type="red_packet_claim",
            description=f"抢到红包 {amount}",
            meta={
                "packet_id": packet.id,
                "chat_id": packet.chat_id,
                "creator_user_id": packet.creator_user_id,
            },
            is_consumed=True,
            commit=False,
        )
        await session.commit()
        finished = packet.status != "active"
        return {"success": True, "amount": amount, "finished": finished}

    @staticmethod
    async def claim_red_packet(
        session: AsyncSession,
        packet_id: int,
        user_id: int,
        chat_id: int | None = None,
    ) -> dict[str, Any]:
        now_ts = now()
        packet_stmt = select(RedPacketModel).where(RedPacketModel.id == packet_id)
        result = await session.execute(packet_stmt)
        packet = result.scalar_one_or_none()
        if not packet:
            return {"success": False, "reason": "红包不存在"}
        if chat_id is not None and int(packet.chat_id) != int(chat_id):
            return {"success": False, "reason": "红包不属于当前聊天"}
        if packet.status != "active":
            return {"success": False, "reason": "红包已结束"}
        if packet.expire_at <= now_ts:
            refunded = await RedPacketService._expire_and_refund(session, packet)
            return {"success": False, "reason": "红包已过期", "expired": True, "refunded": refunded}
        if (
            packet.packet_type == "exclusive"
            and packet.target_user_id is not None
            and int(packet.target_user_id) != int(user_id)
        ):
            return {"success": False, "reason": "这是专属红包"}
        return await RedPacketService._claim_active_packet(session, packet, user_id)

    @staticmethod
    async def _expire_and_refund(session: AsyncSession, packet: RedPacketModel) -> int:
        if packet.status != "active":
            return 0
        remaining = packet.total_amount - packet.taken_amount
        if remaining > 0:
            await CurrencyService.add_currency(
                session=session,
                user_id=packet.creator_user_id,
                amount=remaining,
                event_type="red_packet_refund",
                description=f"红包过期退款 {remaining}",
                meta={
                    "packet_id": packet.id,
                    "chat_id": packet.chat_id,
                },
                is_consumed=True,
                commit=False,
            )
        packet.status = "expired"
        await session.commit()
        return int(remaining) if remaining > 0 else 0
