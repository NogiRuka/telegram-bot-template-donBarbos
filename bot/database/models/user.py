"""
用户模型模块（与《docs/设计文档.md》一致）

只保存最新 aiogram User 对应字段：
- 必填：id、is_bot、first_name
- 可空：last_name、username、language_code、is_premium、added_to_attachment_menu
- 备注：remark
- 审计：created_at/created_by/updated_at/updated_by/is_deleted/deleted_at/deleted_by
"""

from __future__ import annotations
import datetime

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin, big_int_pk


class UserModel(Base, BasicAuditMixin):
    """
    Telegram用户模型类

    存储Telegram用户的完整信息，包括基本资料、状态标志、
    活动统计等数据。

    继承自:
        Base: 基础模型类，提供通用功能
        BasicAuditMixin: 基础审计混入，提供时间戳和软删除功能

    主要功能:
        1. 存储用户基本信息（姓名、用户名、电话等）
        2. 管理用户状态（管理员、封禁、高级用户等）
        3. 记录活动统计数据
        4. 支持软删除和审计追踪

    数据库表名: users
    """

    __tablename__ = "users"

    # ==================== 基本身份信息 ====================

    id: Mapped[big_int_pk] = mapped_column(comment="Telegram 用户 ID（不可为空）")

    is_bot: Mapped[bool] = mapped_column(default=False, nullable=False, comment="是否为机器人，普通用户为0")

    first_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="用户名（必填）")

    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="姓（可空）")

    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True, comment="用户名（可空）")

    language_code: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="用户语言标记（可空）")

    is_premium: Mapped[bool | None] = mapped_column(nullable=True, comment="是否 Telegram Premium 用户（可空）")

    added_to_attachment_menu: Mapped[bool | None] = mapped_column(nullable=True, comment="是否把 bot 加入附件菜单（可空）")


    # ==================== 数据库索引定义 ====================

    __table_args__ = (
        Index("idx_users_created_at", "created_at"),
        Index("idx_users_updated_at", "updated_at"),
    )

    # ==================== 显示配置 ====================

    # 用于__repr__方法显示的关键列
    repr_cols = ("id", "username", "first_name", "is_bot", "is_premium", "is_deleted")

    # ==================== 业务方法 ====================

    def get_display_name(self) -> str:
        """
        获取用户的显示名称

        按优先级返回用户名、全名或名字作为显示名称。

        返回:
            str: 用户的显示名称
        """
        if self.username:
            return f"@{self.username}"
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def get_full_name(self) -> str:
        """
        获取用户的全名

        组合名字和姓氏，如果姓氏不存在则只返回名字。

        返回:
            str: 用户的全名
        """
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name

    def can_use_bot(self) -> bool:
        """
        判断用户是否可以使用机器人

        检查用户是否被软删除。

        返回:
            bool: True表示可以使用，False表示不可以使用
        """
        return not self.is_deleted

    def soft_delete(self, operated_by_user_id: int | None = None) -> None:
        """
        软删除用户

        标记用户为已删除状态，不会从数据库中物理删除。

        参数:
            operated_by_user_id: 执行删除操作的用户ID，可选
        """
        self.is_deleted = True
        self.deleted_at = datetime.datetime.now()
        self.deleted_by = operated_by_user_id

    def restore(self) -> None:
        """
        恢复已软删除的用户

        将用户从软删除状态恢复为正常状态。
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
