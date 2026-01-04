from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk


class MediaCategoryModel(Base, BasicAuditMixin):
    """媒体库分类模型

    功能说明:
    - 存储媒体库分类信息
    - 支持分类的启用/禁用状态
    - 支持分类排序

    数据库表: emby_media_categories
    """

    __tablename__ = "emby_media_categories"

    id: Mapped[auto_int_pk]

    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="分类名称")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="分类描述")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序顺序")

    def __repr__(self) -> str:
        return f"<MediaCategoryModel(id={self.id}, name='{self.name}', enabled={self.is_enabled})>"
