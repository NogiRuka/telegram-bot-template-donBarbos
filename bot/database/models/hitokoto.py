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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="自增主键")

    hitokoto_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="一言标识")
    hitokoto: Mapped[str] = mapped_column(Text, nullable=False, comment="一言正文。编码方式 unicode。使用 utf-8。")
    type: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
        index=True,
        comment="类型。a-动画 b-漫画 c-游戏 d-文学 e-原创 f-来自网络 g-其他 h-影视 i-诗词 j-网易云 k-哲学 l-抖机灵",
    )
    from_: Mapped[str | None] = mapped_column("from", String(255), nullable=True, comment="一言的出处")
    from_who: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="一言的作者")
    creator: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="添加者")
    creator_uid: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="添加者用户标识")
    reviewer: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="审核员标识")
    uuid: Mapped[str] = mapped_column(String(64), comment="一言唯一标识；可在 https://hitokoto.cn?uuid=[uuid] 查看完整信息")
    commit_from: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="提交方式")
    source_created_at: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="来源添加时间(created_at)")
    length: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="句子长度")

    __table_args__ = (
        Index("idx_hitokoto_type", "type"),
        Index("idx_hitokoto_id", "hitokoto_id"),
    )
