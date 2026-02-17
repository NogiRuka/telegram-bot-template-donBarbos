from __future__ import annotations
import random
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, select, update

from bot.database.models import RedPacketClaimModel, RedPacketModel
from bot.services.currency import CurrencyService
from bot.utils.datetime import now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RedPacketService:
    @staticmethod
    async def create_red_packet(
        session: AsyncSession,
        creator_id: int,
        chat_id: int,
        total_amount: int,
        count: int,
        packet_type: str,
        expire_minutes: int,
        target_user_id: int | None,
        message_text: str | None,
        cover_template_id: int | None,
    ) -> RedPacketModel:
        if total_amount <= 0:
            msg = "⚠️ 红包总金额必须大于 0"
            raise ValueError(msg)
        if count <= 0:
            msg = "⚠️ 红包份数必须大于 0"
            raise ValueError(msg)
        if total_amount < count and packet_type != "exclusive":
            msg = "⚠️ 非专属红包总金额必须大于等于份数"
            raise ValueError(msg)
        if packet_type == "exclusive":
            count = 1
        expire_at = now() + timedelta(minutes=expire_minutes)
        await CurrencyService.add_currency(
            session=session,
            user_id=creator_id,
            amount=-total_amount,
            event_type="red_packet_create",
            description=f"发红包，金额 {total_amount}",
            meta={
                "chat_id": chat_id,
                "packet_type": packet_type,
            },
            is_consumed=True,
            commit=False,
        )
        packet = RedPacketModel(
            chat_id=chat_id,
            message_id=None,
            creator_user_id=creator_id,
            total_amount=total_amount,
            packet_count=count,
            packet_type=packet_type,
            target_user_id=target_user_id,
            taken_count=0,
            taken_amount=0,
            status="active",
            expire_at=expire_at,
            cover_template_id=cover_template_id,
            cover_image_file_id=None,
            message_text=message_text,
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
        return random.randint(min_amount, upper)

    @staticmethod
    async def claim_red_packet(
        session: AsyncSession,
        packet_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        now_ts = now()
        packet_stmt = select(RedPacketModel).where(RedPacketModel.id == packet_id)
        result = await session.execute(packet_stmt)
        packet = result.scalar_one_or_none()
        if not packet:
            return {"success": False, "reason": "红包不存在"}
        if packet.status != "active":
            return {"success": False, "reason": "红包已结束"}
        if packet.expire_at <= now_ts:
            await RedPacketService._expire_and_refund(session, packet)
            return {"success": False, "reason": "红包已过期"}
        if packet.packet_type == "exclusive":
            if packet.target_user_id is not None and packet.target_user_id != user_id:
                return {"success": False, "reason": "这是专属红包"}
        claim_check_stmt = select(RedPacketClaimModel).where(
            and_(RedPacketClaimModel.packet_id == packet.id, RedPacketClaimModel.user_id == user_id)
        )
        claim_check_res = await session.execute(claim_check_stmt)
        existed = claim_check_res.scalar_one_or_none()
        if existed:
            return {"success": False, "reason": "你已经抢过这个红包了"}
        remaining_count = packet.packet_count - packet.taken_count
        remaining_amount = packet.total_amount - packet.taken_amount
        if remaining_count <= 0 or remaining_amount <= 0:
            return {"success": False, "reason": "红包已经被抢完啦"}
        if packet.packet_type == "fixed":
            base = packet.total_amount // packet.packet_count
            amount = base
            if remaining_count == 1:
                amount = remaining_amount
        else:
            amount = RedPacketService._random_amount(remaining_amount, remaining_count)
        new_taken_count = packet.taken_count + 1
        new_taken_amount = packet.taken_amount + amount
        if new_taken_count > packet.packet_count or new_taken_amount > packet.total_amount:
            return {"success": False, "reason": "红包已经被抢完啦"}
        claim = RedPacketClaimModel(
            packet_id=packet.id,
            user_id=user_id,
            amount=amount,
            is_rolled_back=False,
        )
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
    async def _expire_and_refund(session: AsyncSession, packet: RedPacketModel) -> None:
        if packet.status != "active":
            return
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
