from typing import Any

from sqlalchemy import JSON, BigInteger, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class CurrencyTransactionModel(Base, BasicAuditMixin):
    """货币流水模型

    功能说明:
    - 记录用户的每一次代币获取和消耗，用于审计和回溯。

    字段:
    - id: 流水ID (BigInt, PK)
    - user_id: 用户ID (BigInt, FK users.id)
    - amount: 变动数值 (正数为获取，负数为消耗)
    - balance_after: 变动后余额 (快照)
    - event_type: 事件类型 (daily_checkin, redeem_emby 等)
    - description: 流水描述 (人类可读)
    - meta: 扩展信息 (JSON)
    """

    __tablename__ = "currency_transactions"

    id: Mapped[auto_int_pk] = mapped_column(primary_key=True, autoincrement=True, comment="流水ID")

    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False, comment="关联 users.id")

    amount: Mapped[int] = mapped_column(nullable=False, comment="变动数值")

    balance_after: Mapped[int] = mapped_column(nullable=False, comment="变动后余额")

    event_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False, comment="事件类型")

    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="流水描述")

    is_consumed: Mapped[bool] = mapped_column(default=True, comment="是否已消耗(用于功能购买凭证)")

    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="扩展信息")

    __table_args__ = (
        Index("idx_currency_trans_user_event", "user_id", "event_type"),
    )
