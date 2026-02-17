from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class RedPacketModel(Base, BasicAuditMixin):
    __tablename__ = "red_packets"

    id: Mapped[auto_int_pk]

    chat_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    creator_user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)

    total_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    packet_count: Mapped[int] = mapped_column(Integer, nullable=False)
    packet_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_user_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)

    taken_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    taken_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    expire_at: Mapped[DateTime] = mapped_column(DateTime, index=True, nullable=False)

    cover_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cover_image_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    message_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_redpacket_chat_message", "chat_id", "message_id"),
        Index("idx_redpacket_creator", "creator_user_id", "created_at"),
        Index("idx_redpacket_status", "status", "expire_at"),
    )


class RedPacketClaimModel(Base, BasicAuditMixin):
    __tablename__ = "red_packet_claims"

    id: Mapped[auto_int_pk]

    packet_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    is_rolled_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("uniq_red_packet_claim", "packet_id", "user_id", unique=True),
        Index("idx_red_packet_claim_user", "user_id", "created_at"),
    )

