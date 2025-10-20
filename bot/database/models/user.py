"""
用户模型模块

本模块定义了Telegram用户的数据库模型，
包含用户的基本信息、状态标志、统计数据等。

作者: Telegram Bot Template
创建时间: 2024-01-23
最后更新: 2025-10-21
"""

from __future__ import annotations
import datetime

from sqlalchemy import String, Text, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, big_int_pk, BasicAuditMixin


class UserModel(Base, BasicAuditMixin):
    """
    Telegram用户模型类
    
    存储Telegram用户的完整信息，包括基本资料、状态标志、
    推荐关系、活动统计等数据。
    
    继承自:
        Base: 基础模型类，提供通用功能
        BasicAuditMixin: 基础审计混入，提供时间戳和软删除功能
    
    主要功能:
        1. 存储用户基本信息（姓名、用户名、电话等）
        2. 管理用户状态（管理员、封禁、高级用户等）
        3. 记录推荐关系和统计数据
        4. 支持软删除和审计追踪
    
    数据库表名: users
    """
    
    __tablename__ = "users"

    # ==================== 基本身份信息 ====================
    
    id: Mapped[big_int_pk] = mapped_column(
        comment="用户的Telegram ID，作为主键，由Telegram系统分配的唯一标识符"
    )
    
    first_name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="用户的名字，必填字段，最大255字符，来自Telegram用户资料"
    )
    
    last_name: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="用户的姓氏，可选字段，最大255字符，来自Telegram用户资料"
    )
    
    username: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True, 
        index=True,
        comment="用户的Telegram用户名，可选字段，不包含@符号，用于@提及和搜索"
    )
    
    # ==================== 联系方式信息 ====================
    
    phone_number: Mapped[str | None] = mapped_column(
        String(20), 
        nullable=True,
        comment="用户的电话号码，可选字段，格式为国际标准格式（如+86138****1234）"
    )
    
    bio: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="用户的个人简介，可选字段，支持长文本，来自Telegram用户资料"
    )
    
    language_code: Mapped[str | None] = mapped_column(
        String(10), 
        nullable=True,
        comment="用户的语言代码，可选字段，ISO 639-1标准（如zh、en、ru等）"
    )
    
    # ==================== 推荐系统相关 ====================
    
    referrer: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="推荐人信息，可选字段，存储推荐人的标识或描述信息"
    )
    
    referrer_id: Mapped[int | None] = mapped_column(
        BigInteger, 
        nullable=True, 
        index=True,
        comment="推荐人的用户ID，可选字段，外键关联到users表的id字段"
    )
    
    # ==================== 活动时间记录 ====================
    
    last_activity_at: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True, 
        index=True,
        comment="用户最后活动时间，可选字段，记录用户最后一次与机器人交互的时间"
    )
    
    # ==================== 用户状态标志 ====================
    
    is_admin: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="管理员标志，默认False，True表示该用户具有管理员权限"
    )
    
    is_suspicious: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="可疑用户标志，默认False，True表示该用户被标记为可疑，需要特别关注"
    )
    
    is_block: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="封禁状态标志，默认False，True表示该用户被封禁，无法使用机器人功能"
    )
    
    is_premium: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="高级用户标志，默认False，True表示该用户是Telegram Premium用户"
    )
    
    is_bot: Mapped[bool] = mapped_column(
        default=False,
        comment="机器人标志，默认False，True表示该账号是机器人而非真实用户"
    )
    
    # ==================== 统计数据 ====================
    
    message_count: Mapped[int] = mapped_column(
        default=0,
        comment="消息计数，默认0，记录用户发送给机器人的消息总数，用于统计分析"
    )
    
    # ==================== 数据库索引定义 ====================
    
    __table_args__ = (
        # 时间相关索引，用于按时间查询和排序
        Index('idx_users_created_at', 'created_at'),  # 创建时间索引，用于按注册时间查询用户
        Index('idx_users_updated_at', 'updated_at'),  # 更新时间索引，用于查询最近更新的用户
        Index('idx_users_last_activity', 'last_activity_at'),  # 最后活动时间索引，用于查询活跃用户和僵尸用户
        
        # 推荐系统索引
        Index('idx_users_referrer_id', 'referrer_id'),  # 推荐人ID索引，用于查询某个用户推荐的所有用户
        
        # 状态组合索引，用于复杂查询
        Index('idx_users_status', 'is_block', 'is_suspicious'),  # 用户状态组合索引，用于查询封禁和可疑用户
        Index('idx_users_admin_premium', 'is_admin', 'is_premium'),  # 管理员和高级用户组合索引，用于权限相关查询
        
        # 软删除相关索引（继承自BasicAuditMixin）
        Index('idx_users_deleted', 'is_deleted'),  # 软删除状态索引，用于过滤已删除用户
        Index('idx_users_deleted_at', 'deleted_at'),  # 删除时间索引，用于查询删除历史
    )
    
    # ==================== 显示配置 ====================
    
    # 用于__repr__方法显示的关键列
    repr_cols = ('id', 'username', 'first_name', 'is_admin', 'is_premium', 'is_deleted')
    
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
        elif self.last_name:
            return f"{self.first_name} {self.last_name}"
        else:
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
        else:
            return self.first_name
    
    def is_active_user(self, days: int = 30) -> bool:
        """
        判断用户是否为活跃用户
        
        根据最后活动时间判断用户是否在指定天数内有活动。
        
        参数:
            days: 活跃天数阈值，默认30天
            
        返回:
            bool: True表示活跃用户，False表示非活跃用户
        """
        if not self.last_activity_at:
            return False
        
        threshold = datetime.datetime.now() - datetime.timedelta(days=days)
        return self.last_activity_at > threshold
    
    def can_use_bot(self) -> bool:
        """
        判断用户是否可以使用机器人
        
        检查用户是否被封禁或软删除。
        
        返回:
            bool: True表示可以使用，False表示不可以使用
        """
        return not self.is_block and not self.is_deleted
    
    def increment_message_count(self) -> None:
        """
        增加用户消息计数
        
        每当用户发送消息时调用此方法增加计数。
        """
        if self.message_count is None:
            self.message_count = 0
        self.message_count += 1
        self.last_activity_at = datetime.datetime.now()
    
    def soft_delete(self, operated_by_user_id: int | None = None) -> None:
        """
        软删除用户
        
        标记用户为已删除状态，不会从数据库中物理删除。
        
        参数:
            operated_by_user_id: 执行删除操作的用户ID，可选
        """
        self.is_deleted = True
        self.deleted_at = datetime.datetime.now()
        self.operated_by = operated_by_user_id
    
    def restore(self) -> None:
        """
        恢复已软删除的用户
        
        将用户从软删除状态恢复为正常状态。
        """
        self.is_deleted = False
        self.deleted_at = None
        self.operated_by = None
