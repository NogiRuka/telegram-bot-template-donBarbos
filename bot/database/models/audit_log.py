from __future__ import annotations
from enum import Enum

from sqlalchemy import String, Text, Index, BigInteger, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, created_at


class ActionType(str, Enum):
    """操作类型枚举"""
    # 用户操作
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_BLOCK = "user_block"
    USER_UNBLOCK = "user_unblock"
    USER_PROMOTE = "user_promote"
    USER_DEMOTE = "user_demote"
    
    # 消息操作
    MESSAGE_SEND = "message_send"
    MESSAGE_DELETE = "message_delete"
    MESSAGE_EDIT = "message_edit"
    
    # 系统操作
    CONFIG_UPDATE = "config_update"
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    
    # 管理操作
    ADMIN_LOGIN = "admin_login"
    ADMIN_LOGOUT = "admin_logout"
    ADMIN_ACTION = "admin_action"
    
    # 其他
    OTHER = "other"


class AuditLogModel(Base):
    """
    操作日志模型类，用于记录系统操作审计信息
    
    字段说明：
    - id: 日志ID（自增主键）
    - user_id: 操作用户ID
    - action_type: 操作类型
    - target_type: 目标类型（如user、message、config等）
    - target_id: 目标ID
    - description: 操作描述
    - details: 详细信息（JSON格式）
    - ip_address: IP地址
    - user_agent: 用户代理
    - created_at: 创建时间
    """
    __tablename__ = "audit_logs"

    # 主键（自增）
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 操作者信息
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    
    # 操作信息
    action_type: Mapped[ActionType] = mapped_column(SQLEnum(ActionType), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    target_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # 请求信息
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # 支持IPv6
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[created_at]
    
    # 索引定义
    __table_args__ = (
        Index('idx_audit_logs_user_created', 'user_id', 'created_at'),
        Index('idx_audit_logs_action_created', 'action_type', 'created_at'),
        Index('idx_audit_logs_target', 'target_type', 'target_id'),
        Index('idx_audit_logs_created', 'created_at'),
    )
    
    # 用于repr显示的列
    repr_cols = ('id', 'user_id', 'action_type', 'target_type', 'created_at')