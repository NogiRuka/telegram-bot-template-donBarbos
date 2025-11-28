"""一言(Hitokoto)模型定义"""

from __future__ import annotations

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, RemarkMixin, SoftDeleteMixin, auto_int_pk


class HitokotoModel(Base, SoftDeleteMixin, RemarkMixin):
    """一言(Hitokoto)数据模型

    功能说明:
    - 存储从 Hitokoto 接口返回的一言信息

    输入参数:
    - 无

    返回值:
    - 无
    """

    __tablename__ = "hitokoto"

    id: Mapped[auto_int_pk]

    hitokoto_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Hitokoto 原始ID(可空)"
    )

    uuid: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        unique=False,
        comment="Hitokoto 唯一标识UUID(可空)"
    )

    hitokoto: Mapped[str] = mapped_column(Text, nullable=False, comment="一言正文")

    type: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True, comment="类型代码")

    source: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="出处(from)")

    from_who: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="作者(from_who)")

    creator: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="添加者")

    creator_uid: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="添加者UID")

    reviewer: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="审核员标识")

    commit_from: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="提交方式")

    source_created_at: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源创建时间")

    length: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="句子长度")

    __table_args__ = (
        Index("idx_hitokoto_uuid", "uuid"),
        Index("idx_hitokoto_type", "type"),
        Index("idx_hitokoto_hid", "hitokoto_id"),
    )

