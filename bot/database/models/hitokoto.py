from __future__ import annotations

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class HitokotoModel(Base, BasicAuditMixin):
    """Hitokoto(一言)数据模型

    功能说明:
    - 存储从 Hitokoto 接口返回的一言信息, 字段与接口返回保持一致, 其中接口的 `created_at` 存入 `source_created_at`

    输入参数:
    - 无

    返回值:
    - 无
    """

    __tablename__ = "hitokoto"

    # 使用 uuid 作为主键以避免与审计字段冲突
    uuid: Mapped[str] = mapped_column(String(64), primary_key=True, comment="一言唯一标识UUID")

    # 接口字段
    id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="一言标识(id)")
    hitokoto: Mapped[str] = mapped_column(Text, nullable=False, comment="一言正文")
    type: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True, comment="类型代码(type)")
    from_: Mapped[str | None] = mapped_column("from", String(255), nullable=True, comment="出处(from)")
    from_who: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="作者(from_who)")
    creator: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="添加者(creator)")
    creator_uid: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="添加者用户标识(creator_uid)")
    reviewer: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="审核员标识(reviewer)")
    commit_from: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="提交方式(commit_from)")
    source_created_at: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源创建时间(created_at)")
    length: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="句子长度(length)")

    __table_args__ = (
        Index("idx_hitokoto_type", "type"),
        Index("idx_hitokoto_id", "id"),
    )

