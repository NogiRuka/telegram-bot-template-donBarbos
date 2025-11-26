"""
用户信息历史快照模型

保存 users 表的快照，用于追踪用户信息变更历史。
"""

from __future__ import annotations
import datetime

from sqlalchemy import BigInteger, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class UserHistoryModel(Base, BasicAuditMixin):
    """用户历史快照模型

    功能说明:
    - 保存用户信息的历史记录，仅包含 aiogram User 对应字段与审计字段

    字段:
    - history_id: 自增主键
    - user_id: 用户 ID
    - is_bot: 是否机器人
    - first_name: 名
    - last_name: 姓（可空）
    - username: 用户名（可空）
    - language_code: 语言代码（可空）
    - is_premium: 是否高级用户（可空）
    - added_to_attachment_menu: 是否加入附件菜单（可空）
    - snapshot_at: 快照时间（默认当前）
    - remark: 备注
    - 审计字段: created_at/updated_at/is_deleted/deleted_at/created_by/updated_by/deleted_by

    返回值:
    - 无
    """

    __tablename__ = "user_history"

    # 主键ID
    history_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")

    # 用户 ID
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="用户 ID")

    # aiogram User 对应字段
    is_bot: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否机器人")
    first_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="用户名")
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="姓")
    username: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="用户名")
    language_code: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="语言代码")
    is_premium: Mapped[bool | None] = mapped_column(nullable=True, comment="是否 Premium 用户")
    added_to_attachment_menu: Mapped[bool | None] = mapped_column(nullable=True, comment="是否加入附件菜单")

    # 快照时间
    snapshot_at: Mapped[datetime.datetime] = mapped_column(nullable=False, default=datetime.datetime.now, comment="快照时间")


    __table_args__ = (
        Index("idx_user_history_user_snapshot", "user_id", "snapshot_at"),
    )
