"""
审计日志模型模块

本模块定义了系统操作审计日志的数据库模型，
用于记录用户操作、系统事件、管理行为等重要活动。

作者: Telegram Bot Template
创建时间: 2024-01-23
最后更新: 2025-10-21
"""

from __future__ import annotations
from enum import Enum
import datetime

from sqlalchemy import String, Text, Index, BigInteger, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, auto_int_pk, TimestampMixin


class ActionType(str, Enum):
    """
    操作类型枚举
    
    定义了系统中所有可能的操作类型，用于分类和统计不同的用户行为。
    每个操作类型都有明确的语义，便于日志分析和审计追踪。
    """
    
    # ==================== 用户相关操作 ====================
    USER_CREATE = "user_create"        # 用户注册/创建
    USER_UPDATE = "user_update"        # 用户信息更新
    USER_DELETE = "user_delete"        # 用户删除/注销
    USER_BLOCK = "user_block"          # 用户封禁
    USER_UNBLOCK = "user_unblock"      # 用户解封
    USER_PROMOTE = "user_promote"      # 用户提权（如设为管理员）
    USER_DEMOTE = "user_demote"        # 用户降权（如取消管理员）
    USER_LOGIN = "user_login"          # 用户登录
    USER_LOGOUT = "user_logout"        # 用户登出
    
    # ==================== 消息相关操作 ====================
    MESSAGE_SEND = "message_send"      # 发送消息
    MESSAGE_DELETE = "message_delete"  # 删除消息
    MESSAGE_EDIT = "message_edit"      # 编辑消息
    MESSAGE_FORWARD = "message_forward" # 转发消息
    MESSAGE_REPLY = "message_reply"    # 回复消息
    
    # ==================== 配置相关操作 ====================
    CONFIG_CREATE = "config_create"    # 创建配置项
    CONFIG_UPDATE = "config_update"    # 更新配置项
    CONFIG_DELETE = "config_delete"    # 删除配置项
    CONFIG_RESET = "config_reset"      # 重置配置项
    
    # ==================== 系统相关操作 ====================
    SYSTEM_START = "system_start"      # 系统启动
    SYSTEM_STOP = "system_stop"        # 系统停止
    SYSTEM_RESTART = "system_restart"  # 系统重启
    SYSTEM_BACKUP = "system_backup"    # 系统备份
    SYSTEM_RESTORE = "system_restore"  # 系统恢复
    
    # ==================== 管理相关操作 ====================
    ADMIN_LOGIN = "admin_login"        # 管理员登录
    ADMIN_LOGOUT = "admin_logout"      # 管理员登出
    ADMIN_ACTION = "admin_action"      # 管理员操作
    ADMIN_QUERY = "admin_query"        # 管理员查询
    ADMIN_EXPORT = "admin_export"      # 管理员导出数据
    
    # ==================== 安全相关操作 ====================
    SECURITY_LOGIN_FAIL = "security_login_fail"        # 登录失败
    SECURITY_SUSPICIOUS = "security_suspicious"        # 可疑行为
    SECURITY_RATE_LIMIT = "security_rate_limit"        # 触发限流
    SECURITY_PERMISSION_DENY = "security_permission_deny"  # 权限拒绝
    
    # ==================== 其他操作 ====================
    OTHER = "other"                    # 其他未分类操作


class AuditLogModel(Base, TimestampMixin):
    """
    审计日志模型类
    
    记录系统中所有重要操作的详细信息，包括操作者、操作类型、
    目标对象、操作描述、请求信息等，用于安全审计和行为分析。
    
    继承自:
        Base: 基础模型类，提供通用功能
        TimestampMixin: 时间戳混入，提供创建和更新时间字段
    
    主要功能:
        1. 记录用户操作行为和系统事件
        2. 支持详细的操作描述和JSON格式的扩展信息
        3. 记录请求来源信息（IP地址、用户代理等）
        4. 提供多维度的索引支持高效查询
        5. 支持操作类型分类和统计分析
    
    数据库表名: audit_logs
    """
    
    __tablename__ = "audit_logs"

    # ==================== 主键字段 ====================
    
    id: Mapped[auto_int_pk] = mapped_column(
        comment="审计日志的唯一标识符，自增主键，用于唯一标识每条日志记录"
    )
    
    # ==================== 操作者信息 ====================
    
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True, 
        index=True,
        comment="执行操作的用户ID，可选字段，关联到users表，系统操作时可为空"
    )
    
    operator_name: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="操作者名称，可选字段，用于记录操作者的显示名称或系统标识"
    )
    
    # ==================== 操作信息 ====================
    
    action_type: Mapped[ActionType] = mapped_column(
        SQLEnum(ActionType), 
        nullable=False, 
        index=True,
        comment="操作类型，必填字段，使用ActionType枚举值，用于分类和统计操作"
    )
    
    target_type: Mapped[str | None] = mapped_column(
        String(100), 
        nullable=True, 
        index=True,
        comment="目标对象类型，可选字段，如user、message、config等，用于标识操作的目标类型"
    )
    
    target_id: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True, 
        index=True,
        comment="目标对象ID，可选字段，目标对象的唯一标识符，支持字符串格式以兼容不同类型的ID"
    )
    
    description: Mapped[str] = mapped_column(
        Text, 
        nullable=False,
        comment="操作描述，必填字段，详细描述本次操作的内容和目的，支持长文本"
    )
    
    details: Mapped[dict | None] = mapped_column(
        JSON, 
        nullable=True,
        comment="操作详情，可选字段，JSON格式存储操作的详细信息、参数、结果等扩展数据"
    )
    
    # ==================== 请求信息 ====================
    
    ip_address: Mapped[str | None] = mapped_column(
        String(45), 
        nullable=True, 
        index=True,
        comment="客户端IP地址，可选字段，支持IPv4和IPv6格式，用于安全审计和地理位置分析"
    )
    
    user_agent: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="用户代理字符串，可选字段，记录客户端浏览器或应用信息，用于设备识别"
    )
    
    session_id: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="会话ID，可选字段，用于关联同一会话中的多个操作，便于行为分析"
    )
    
    # ==================== 结果信息 ====================
    
    is_success: Mapped[bool] = mapped_column(
        default=True, 
        index=True,
        comment="操作是否成功，默认True，用于统计成功率和识别失败操作"
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="错误信息，可选字段，当操作失败时记录具体的错误描述"
    )
    
    duration_ms: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="操作耗时，可选字段，单位毫秒，用于性能分析和优化"
    )
    
    # ==================== 数据库索引定义 ====================
    
    __table_args__ = (
        # 索引定义 - 用于提高查询性能和支持复杂查询
        Index('idx_audit_logs_user_created', 'user_id', 'created_at'),  # 用户操作历史索引，用于查询特定用户的操作记录
        Index('idx_audit_logs_action_created', 'action_type', 'created_at'),  # 操作类型时间索引，用于按操作类型和时间查询
        Index('idx_audit_logs_target', 'target_type', 'target_id'),  # 目标对象索引，用于查询特定对象的操作历史
        Index('idx_audit_logs_created', 'created_at'),  # 创建时间索引，用于时间范围查询和日志清理
        Index('idx_audit_logs_ip_created', 'ip_address', 'created_at'),  # IP地址时间索引，用于安全分析和异常检测
        Index('idx_audit_logs_success_action', 'is_success', 'action_type'),  # 操作结果统计索引，用于成功率分析
        Index('idx_audit_logs_session', 'session_id', 'created_at'),  # 会话行为分析索引，用于追踪会话中的操作序列
    )
    
    # ==================== 显示配置 ====================
    
    # 用于__repr__方法显示的关键列
    repr_cols = ('id', 'user_id', 'action_type', 'target_type', 'is_success', 'created_at')
    
    # ==================== 业务方法 ====================
    
    def get_operation_summary(self) -> str:
        """
        获取操作摘要
        
        生成简洁的操作摘要，包含操作者、操作类型和目标信息。
        
        返回:
            str: 操作摘要字符串
        """
        operator = self.operator_name or f"用户{self.user_id}" if self.user_id else "系统"
        target = f"{self.target_type}({self.target_id})" if self.target_type and self.target_id else "未知目标"
        status = "成功" if self.is_success else "失败"
        
        return f"{operator} {self.action_type.value} {target} - {status}"
    
    def is_security_related(self) -> bool:
        """
        判断是否为安全相关操作
        
        检查操作类型是否属于安全相关类别。
        
        返回:
            bool: True表示安全相关操作，False表示普通操作
        """
        security_actions = {
            ActionType.SECURITY_LOGIN_FAIL,
            ActionType.SECURITY_SUSPICIOUS,
            ActionType.SECURITY_RATE_LIMIT,
            ActionType.SECURITY_PERMISSION_DENY,
            ActionType.USER_BLOCK,
            ActionType.USER_UNBLOCK,
        }
        return self.action_type in security_actions
    
    def is_admin_operation(self) -> bool:
        """
        判断是否为管理员操作
        
        检查操作类型是否属于管理员操作类别。
        
        返回:
            bool: True表示管理员操作，False表示普通操作
        """
        admin_actions = {
            ActionType.ADMIN_LOGIN,
            ActionType.ADMIN_LOGOUT,
            ActionType.ADMIN_ACTION,
            ActionType.ADMIN_QUERY,
            ActionType.ADMIN_EXPORT,
            ActionType.USER_PROMOTE,
            ActionType.USER_DEMOTE,
        }
        return self.action_type in admin_actions
    
    def get_duration_display(self) -> str:
        """
        获取耗时的显示格式
        
        将毫秒耗时转换为易读的格式。
        
        返回:
            str: 格式化的耗时字符串
        """
        if self.duration_ms is None:
            return "未知"
        
        if self.duration_ms < 1000:
            return f"{self.duration_ms}ms"
        elif self.duration_ms < 60000:
            return f"{self.duration_ms / 1000:.2f}s"
        else:
            minutes = self.duration_ms // 60000
            seconds = (self.duration_ms % 60000) / 1000
            return f"{minutes}m{seconds:.1f}s"
    
    @classmethod
    def create_log(
        cls,
        action_type: ActionType,
        description: str,
        user_id: int | None = None,
        operator_name: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        session_id: str | None = None,
        is_success: bool = True,
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> "AuditLogModel":
        """
        创建审计日志记录
        
        便捷方法用于创建新的审计日志记录。
        
        参数:
            action_type: 操作类型
            description: 操作描述
            user_id: 用户ID，可选
            operator_name: 操作者名称，可选
            target_type: 目标类型，可选
            target_id: 目标ID，可选
            details: 详细信息，可选
            ip_address: IP地址，可选
            user_agent: 用户代理，可选
            session_id: 会话ID，可选
            is_success: 是否成功，默认True
            error_message: 错误信息，可选
            duration_ms: 耗时毫秒数，可选
            
        返回:
            AuditLogModel: 新创建的审计日志实例
        """
        return cls(
            action_type=action_type,
            description=description,
            user_id=user_id,
            operator_name=operator_name,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            is_success=is_success,
            error_message=error_message,
            duration_ms=duration_ms,
        )