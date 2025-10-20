"""
用户状态模型模块

本模块定义了用户会话状态的数据库模型，
用于存储和管理Telegram机器人的FSM（有限状态机）状态信息。

作者: Telegram Bot Template
创建时间: 2024-01-23
最后更新: 2025-10-21
"""

from __future__ import annotations
import datetime
import json
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import String, Text, Index, BigInteger, JSON, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, TimestampMixin


class StateType(str, Enum):
    """
    状态类型枚举
    
    定义了系统支持的各种状态类型，
    用于分类和管理不同场景的用户状态。
    """
    
    # ==================== 基础状态 ====================
    IDLE = "idle"                          # 空闲状态，用户没有进行任何操作
    WAITING_INPUT = "waiting_input"        # 等待用户输入状态
    PROCESSING = "processing"              # 处理中状态，系统正在处理用户请求
    
    # ==================== 注册流程状态 ====================
    REGISTRATION_START = "registration_start"        # 注册开始状态
    REGISTRATION_NAME = "registration_name"          # 等待输入姓名状态
    REGISTRATION_EMAIL = "registration_email"        # 等待输入邮箱状态
    REGISTRATION_PHONE = "registration_phone"        # 等待输入电话状态
    REGISTRATION_CONFIRM = "registration_confirm"    # 注册确认状态
    
    # ==================== 设置配置状态 ====================
    SETTINGS_MENU = "settings_menu"                  # 设置菜单状态
    SETTINGS_LANGUAGE = "settings_language"          # 语言设置状态
    SETTINGS_TIMEZONE = "settings_timezone"          # 时区设置状态
    SETTINGS_NOTIFICATIONS = "settings_notifications"  # 通知设置状态
    SETTINGS_PRIVACY = "settings_privacy"            # 隐私设置状态
    
    # ==================== 内容创建状态 ====================
    CONTENT_CREATE = "content_create"                # 内容创建状态
    CONTENT_TITLE = "content_title"                  # 等待输入标题状态
    CONTENT_DESCRIPTION = "content_description"      # 等待输入描述状态
    CONTENT_UPLOAD = "content_upload"                # 等待上传文件状态
    CONTENT_PREVIEW = "content_preview"              # 内容预览状态
    
    # ==================== 搜索查询状态 ====================
    SEARCH_QUERY = "search_query"                    # 搜索查询状态
    SEARCH_FILTER = "search_filter"                  # 搜索过滤状态
    SEARCH_RESULTS = "search_results"                # 搜索结果状态
    
    # ==================== 支付流程状态 ====================
    PAYMENT_START = "payment_start"                  # 支付开始状态
    PAYMENT_METHOD = "payment_method"                # 选择支付方式状态
    PAYMENT_CONFIRM = "payment_confirm"              # 支付确认状态
    PAYMENT_PROCESSING = "payment_processing"        # 支付处理中状态
    PAYMENT_SUCCESS = "payment_success"              # 支付成功状态
    PAYMENT_FAILED = "payment_failed"                # 支付失败状态
    
    # ==================== 客服对话状态 ====================
    SUPPORT_MENU = "support_menu"                    # 客服菜单状态
    SUPPORT_CATEGORY = "support_category"            # 选择问题分类状态
    SUPPORT_DESCRIPTION = "support_description"      # 描述问题状态
    SUPPORT_WAITING = "support_waiting"              # 等待客服回复状态
    SUPPORT_CHATTING = "support_chatting"            # 与客服对话状态
    
    # ==================== 游戏状态 ====================
    GAME_MENU = "game_menu"                          # 游戏菜单状态
    GAME_PLAYING = "game_playing"                    # 游戏进行中状态
    GAME_PAUSED = "game_paused"                      # 游戏暂停状态
    GAME_FINISHED = "game_finished"                  # 游戏结束状态
    
    # ==================== 管理员状态 ====================
    ADMIN_MENU = "admin_menu"                        # 管理员菜单状态
    ADMIN_USER_MANAGE = "admin_user_manage"          # 用户管理状态
    ADMIN_CONTENT_REVIEW = "admin_content_review"    # 内容审核状态
    ADMIN_SYSTEM_CONFIG = "admin_system_config"      # 系统配置状态
    ADMIN_STATISTICS = "admin_statistics"            # 统计查看状态
    
    # ==================== 错误状态 ====================
    ERROR_OCCURRED = "error_occurred"                # 发生错误状态
    ERROR_RECOVERY = "error_recovery"                # 错误恢复状态
    
    # ==================== 自定义状态 ====================
    CUSTOM_STATE = "custom_state"                    # 自定义状态
    OTHER = "other"                                  # 其他状态


class StatePriority(str, Enum):
    """
    状态优先级枚举
    
    定义了状态的优先级，用于状态冲突时的处理。
    """
    
    LOW = "low"          # 低优先级
    NORMAL = "normal"    # 普通优先级
    HIGH = "high"        # 高优先级
    CRITICAL = "critical"  # 关键优先级


class UserStateModel(Base, TimestampMixin):
    """
    用户状态模型类
    
    存储和管理Telegram机器人的用户会话状态信息，
    支持有限状态机（FSM）的状态管理和数据持久化。
    
    继承自:
        Base: 基础模型类，提供通用功能
        TimestampMixin: 时间戳混入，提供创建和更新时间字段
    
    主要功能:
        1. 存储用户的当前状态和状态数据
        2. 支持状态的过期和自动清理
        3. 提供状态历史记录和回滚功能
        4. 支持多聊天会话的状态隔离
        5. 提供状态数据的序列化和反序列化
    
    数据库表名: user_states
    """
    
    __tablename__ = "user_states"

    # ==================== 主键字段 ====================
    
    user_id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True,
        comment="用户ID，复合主键的一部分，标识状态所属的用户"
    )
    
    chat_id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True,
        comment="聊天ID，复合主键的一部分，标识状态所属的聊天会话"
    )
    
    # ==================== 状态信息字段 ====================
    
    state: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True, 
        index=True,
        comment="当前状态，可选字段，存储用户的当前FSM状态标识"
    )
    
    state_type: Mapped[StateType | None] = mapped_column(
        String(100), 
        nullable=True, 
        index=True,
        comment="状态类型，可选字段，使用StateType枚举值标识状态的分类"
    )
    
    previous_state: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="前一个状态，可选字段，用于状态回滚和历史追踪"
    )
    
    priority: Mapped[StatePriority] = mapped_column(
        String(20), 
        nullable=False, 
        default=StatePriority.NORMAL,
        comment="状态优先级，必填字段，用于状态冲突时的处理，默认为普通优先级"
    )
    
    # ==================== 状态数据字段 ====================
    
    data: Mapped[dict | None] = mapped_column(
        JSON, 
        nullable=True,
        comment="状态数据，可选字段，JSON格式存储状态相关的数据和参数"
    )
    
    context: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="状态上下文，可选字段，存储状态的详细上下文信息"
    )
    
    state_metadata: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="状态元数据，可选字段，JSON格式存储额外的状态元信息"
    )
    
    # ==================== 时间管理字段 ====================
    
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True, 
        index=True,
        comment="过期时间，可选字段，状态的过期时间，过期后状态将被自动清理"
    )
    
    last_activity_at: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True, 
        index=True,
        comment="最后活动时间，可选字段，记录用户在此状态下的最后活动时间"
    )
    
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer, 
        nullable=True,
        comment="持续时间，可选字段，状态持续的秒数，用于统计和分析"
    )
    
    # ==================== 状态控制字段 ====================
    
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=True, 
        index=True,
        comment="是否激活，必填字段，标识状态是否处于激活状态，默认为True"
    )
    
    is_persistent: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="是否持久化，必填字段，标识状态是否需要持久保存，默认为False"
    )
    
    is_locked: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="是否锁定，必填字段，标识状态是否被锁定不可修改，默认为False"
    )
    
    # ==================== 统计字段 ====================
    
    step_count: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0,
        comment="步骤计数，必填字段，记录在当前状态下执行的步骤数量，默认为0"
    )
    
    retry_count: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0,
        comment="重试次数，必填字段，记录状态操作的重试次数，默认为0"
    )
    
    error_count: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=0,
        comment="错误次数，必填字段，记录在当前状态下发生的错误次数，默认为0"
    )
    
    # ==================== 扩展字段 ====================
    
    tags: Mapped[str | None] = mapped_column(
        String(500), 
        nullable=True,
        comment="标签，可选字段，逗号分隔的标签列表，用于状态的分类和搜索"
    )
    
    notes: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="备注，可选字段，状态的备注信息，用于调试和说明"
    )
    
    # ==================== 数据库索引定义 ====================
    
    __table_args__ = (
        # 状态索引，用于按状态查询
        Index('idx_user_states_state', 'state', 'state_type'),
        
        # 过期时间索引，用于清理过期状态
        Index('idx_user_states_expires', 'expires_at', 'is_active'),
        
        # 活动时间索引，用于查询最近活动
        Index('idx_user_states_activity', 'last_activity_at', 'is_active'),
        
        # 优先级索引，用于按优先级查询
        Index('idx_user_states_priority', 'priority', 'is_active'),
        
        # 状态控制索引，用于查询特定状态
        Index('idx_user_states_control', 'is_active', 'is_persistent', 'is_locked'),
        
        # 统计索引，用于状态统计分析
        Index('idx_user_states_stats', 'step_count', 'retry_count', 'error_count'),
        
        # 时间戳索引（继承自TimestampMixin）
        Index('idx_user_states_updated', 'updated_at'),
        Index('idx_user_states_created', 'created_at'),
        
        # 复合查询索引，用于复杂查询优化
        Index('idx_user_states_complex', 'user_id', 'state', 'is_active', 'expires_at'),
    )
    
    # ==================== 显示配置 ====================
    
    # 用于__repr__方法显示的关键列
    repr_cols = ('user_id', 'chat_id', 'state', 'state_type', 'is_active', 'updated_at')
    
    # ==================== 业务方法 ====================
    
    def is_expired(self) -> bool:
        """
        检查状态是否已过期
        
        返回:
            bool: True表示已过期，False表示未过期或无过期时间
        """
        if not self.expires_at:
            return False
        return datetime.datetime.utcnow() > self.expires_at
    
    def get_remaining_time(self) -> int | None:
        """
        获取状态剩余时间
        
        返回:
            int | None: 剩余秒数，如果无过期时间则返回None
        """
        if not self.expires_at:
            return None
        
        remaining = self.expires_at - datetime.datetime.utcnow()
        return max(0, int(remaining.total_seconds()))
    
    def extend_expiry(self, seconds: int) -> None:
        """
        延长状态过期时间
        
        参数:
            seconds: 要延长的秒数
        """
        if self.expires_at:
            self.expires_at += datetime.timedelta(seconds=seconds)
        else:
            self.expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
    
    def get_data_value(self, key: str, default: Any = None) -> Any:
        """
        获取状态数据中的特定值
        
        参数:
            key: 数据键
            default: 默认值
            
        返回:
            Any: 数据值或默认值
        """
        if not self.data:
            return default
        return self.data.get(key, default)
    
    def set_data_value(self, key: str, value: Any) -> None:
        """
        设置状态数据中的特定值
        
        参数:
            key: 数据键
            value: 数据值
        """
        if not self.data:
            self.data = {}
        self.data[key] = value
    
    def get_metadata_dict(self) -> Dict[str, Any]:
        """
        获取元数据字典
        
        返回:
            Dict[str, Any]: 元数据字典，如果解析失败则返回空字典
        """
        if not self.state_metadata:
            return {}
        
        try:
            return json.loads(self.state_metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata_dict(self, data: Dict[str, Any]) -> None:
        """
        设置元数据字典
        
        参数:
            data: 要存储的元数据字典
        """
        if data:
            self.state_metadata = json.dumps(data, ensure_ascii=False)
        else:
            self.state_metadata = None
    
    def get_tags_list(self) -> List[str]:
        """
        获取标签列表
        
        返回:
            List[str]: 标签列表
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def set_tags_list(self, tags: List[str]) -> None:
        """
        设置标签列表
        
        参数:
            tags: 标签列表
        """
        self.tags = ','.join(tags) if tags else None
    
    def increment_step(self) -> None:
        """
        增加步骤计数
        """
        self.step_count += 1
        self.last_activity_at = datetime.datetime.utcnow()
    
    def increment_retry(self) -> None:
        """
        增加重试次数
        """
        self.retry_count += 1
    
    def increment_error(self) -> None:
        """
        增加错误次数
        """
        self.error_count += 1
    
    def reset_counters(self) -> None:
        """
        重置所有计数器
        """
        self.step_count = 0
        self.retry_count = 0
        self.error_count = 0
    
    def activate(self) -> None:
        """
        激活状态
        """
        self.is_active = True
        self.last_activity_at = datetime.datetime.utcnow()
    
    def deactivate(self) -> None:
        """
        停用状态
        """
        self.is_active = False
    
    def lock(self) -> None:
        """
        锁定状态
        """
        self.is_locked = True
    
    def unlock(self) -> None:
        """
        解锁状态
        """
        self.is_locked = False
    
    def can_modify(self) -> bool:
        """
        检查状态是否可以修改
        
        返回:
            bool: True表示可以修改，False表示不可修改
        """
        return self.is_active and not self.is_locked and not self.is_expired()
    
    def get_state_display(self) -> str:
        """
        获取状态的显示名称
        
        返回:
            str: 状态显示名称
        """
        if self.state_type:
            type_names = {
                StateType.IDLE: "空闲",
                StateType.WAITING_INPUT: "等待输入",
                StateType.PROCESSING: "处理中",
                StateType.REGISTRATION_START: "注册开始",
                StateType.SETTINGS_MENU: "设置菜单",
                StateType.CONTENT_CREATE: "创建内容",
                StateType.SEARCH_QUERY: "搜索查询",
                StateType.PAYMENT_START: "支付开始",
                StateType.SUPPORT_MENU: "客服菜单",
                StateType.GAME_PLAYING: "游戏中",
                StateType.ADMIN_MENU: "管理菜单",
                StateType.ERROR_OCCURRED: "发生错误",
                # 可以继续添加更多类型的显示名称
            }
            return type_names.get(StateType(self.state_type), self.state_type)
        return self.state or "未知状态"
    
    def get_duration_display(self) -> str:
        """
        获取持续时间的显示格式
        
        返回:
            str: 格式化的持续时间
        """
        if not self.duration_seconds:
            return "0秒"
        
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分钟{seconds}秒"
        else:
            return f"{seconds}秒"
    
    @classmethod
    def create_state(
        cls,
        user_id: int,
        chat_id: int,
        state: str,
        state_type: StateType | None = None,
        data: Dict[str, Any] | None = None,
        expires_in_seconds: int | None = None,
        priority: StatePriority = StatePriority.NORMAL,
        **kwargs
    ) -> "UserStateModel":
        """
        创建用户状态
        
        便捷方法用于创建新的用户状态记录。
        
        参数:
            user_id: 用户ID
            chat_id: 聊天ID
            state: 状态标识
            state_type: 状态类型，可选
            data: 状态数据，可选
            expires_in_seconds: 过期秒数，可选
            priority: 状态优先级，默认为普通
            **kwargs: 其他字段参数
            
        返回:
            UserStateModel: 新创建的用户状态实例
        """
        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in_seconds)
        
        user_state = cls(
            user_id=user_id,
            chat_id=chat_id,
            state=state,
            state_type=state_type,
            data=data,
            expires_at=expires_at,
            priority=priority,
            last_activity_at=datetime.datetime.utcnow(),
            **kwargs
        )
        
        return user_state