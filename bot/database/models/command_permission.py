"""通用命令授权模型。"""

from enum import Enum

from sqlalchemy import BigInteger, CheckConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class CommandPermissionScope(str, Enum):
    """命令授权作用域。"""

    GLOBAL = "global"
    GROUP = "group"


class CommandPermissionModel(Base, BasicAuditMixin):
    """记录用户在全局或指定群组中的命令执行权限。"""

    __tablename__ = "command_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True, comment="获授权用户 ID")
    command_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="授权命令名称")
    scope_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="作用域类型")
    scope_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="稳定作用域标识")
    granted_by_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="授权管理员 ID")

    __table_args__ = (
        CheckConstraint(
            "scope_type IN ('global', 'group')",
            name="ck_command_permissions_scope_type",
        ),
        UniqueConstraint(
            "user_id",
            "command_name",
            "scope_key",
            name="uq_command_permissions_user_command_scope",
        ),
        Index(
            "idx_command_permissions_lookup",
            "scope_key",
            "command_name",
            "is_deleted",
        ),
    )

    repr_cols = (
        "id",
        "user_id",
        "command_name",
        "scope_type",
        "scope_key",
        "granted_by_user_id",
        "is_deleted",
    )
