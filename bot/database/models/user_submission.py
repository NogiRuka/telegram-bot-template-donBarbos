from __future__ import annotations
from typing import TYPE_CHECKING

import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.models.base import Base, BasicAuditMixin, auto_int_pk

if TYPE_CHECKING:
    from bot.database.models.media_category import MediaCategoryModel


class UserSubmissionModel(Base, BasicAuditMixin):
    """用户求片/投稿模型

    功能说明:
    - 存储用户的求片和投稿内容
    - 支持分类管理（request=求片，submit=投稿）
    - 支持审核流程（待审核、已通过、已拒绝）
    - 支持奖励机制（基础奖励+额外奖励）

    数据库表: user_submissions
    """

    __tablename__ = "user_submissions"

    id: Mapped[auto_int_pk]

    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题，必填")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="描述")

    # 类型和分类
    type: Mapped[str] = mapped_column(String(20), nullable=False, comment="类型：request=求片，submit=投稿")
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="分类ID，必填")
    category: Mapped[MediaCategoryModel] = relationship(
        "MediaCategoryModel",
        primaryjoin="UserSubmissionModel.category_id == MediaCategoryModel.id",
        foreign_keys="[UserSubmissionModel.category_id]",
        lazy="selectin"
    )

    # 状态管理
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="状态：pending=待审核，approved=已通过，rejected=已拒绝"
    )

    # 奖励机制
    reward_base: Mapped[int] = mapped_column(Integer, default=0, comment="基础奖励")
    reward_bonus: Mapped[int] = mapped_column(Integer, default=0, comment="额外奖励")

    # 图片支持
    image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Telegram图片File ID")
    image_file_unique_id: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Telegram图片File Unique ID")

    # 审核信息
    reviewer_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="审核者用户ID")
    review_time: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核评论")

    # 投稿者信息
    submitter_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="投稿者用户ID")

    # 扩展数据
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="扩展数据")

    # 索引
    __table_args__ = (
        Index("idx_user_submissions_type", "type"),
        Index("idx_user_submissions_status", "status"),
        Index("idx_user_submissions_submitter", "submitter_id"),
        Index("idx_user_submissions_category", "category_id"),
        Index("idx_user_submissions_created", "created_at"),
    )

    repr_cols = ("id", "title", "type", "status", "submitter_id")
