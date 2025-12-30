"""
群组配置模型模块

本模块定义了群组配置的数据库模型，
用于管理群组消息保存设置和相关配置。

作者: Telegram Bot Template
创建时间: 2025-01-21
最后更新: 2025-01-21
"""

from __future__ import annotations
import datetime
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class GroupType(str, Enum):
    """
    群组类型枚举

    定义了Telegram支持的群组类型。
    """

    GROUP = "group"  # 普通群组
    SUPERGROUP = "supergroup"  # 超级群组
    CHANNEL = "channel"  # 频道


class MessageSaveMode(str, Enum):
    """
    消息保存模式枚举

    定义了不同的消息保存策略。
    """

    ALL = "all"  # 保存所有消息
    TEXT_ONLY = "text_only"  # 仅保存文本消息
    MEDIA_ONLY = "media_only"  # 仅保存媒体消息
    IMPORTANT_ONLY = "important_only"  # 仅保存重要消息（置顶、回复等）
    DISABLED = "disabled"  # 禁用消息保存


class GroupConfigModel(Base, BasicAuditMixin):
    """
    群组配置模型类

    存储群组的消息保存配置和相关设置，
    用于控制哪些群组需要保存消息以及保存策略。

    继承自:
        Base: 基础模型类，提供通用功能
        BasicAuditMixin: 基础审计混入，提供时间戳、操作者和软删除字段

    主要功能:
        1. 管理群组消息保存的开关状态
        2. 配置不同群组的消息保存策略
        3. 设置消息保存的时间范围和数量限制
        4. 管理群组的基本信息和权限设置
        5. 支持群组配置的批量管理

    数据库表名: group_configs
    """

    __tablename__ = "group_configs"

    # ==================== 主键字段 ====================

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="群组配置ID，自增主键，唯一标识一条群组配置记录"
    )

    # ==================== Telegram标识字段 ====================

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        index=True,
        comment="聊天ID，必填字段，群组的Telegram聊天ID，确保唯一性",
    )

    chat_title: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="群组标题，可选字段，群组的显示名称"
    )

    chat_username: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, comment="群组用户名，可选字段，群组的@用户名（如果有）"
    )

    group_type: Mapped[GroupType] = mapped_column(
        SQLEnum(GroupType), nullable=False, index=True, comment="群组类型，必填字段，使用GroupType枚举值标识群组类型"
    )

    # ==================== 消息保存配置字段 ====================

    is_message_save_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, comment="是否启用消息保存，默认False，True表示该群组启用消息保存功能"
    )

    message_save_mode: Mapped[MessageSaveMode] = mapped_column(
        SQLEnum(MessageSaveMode),
        default=MessageSaveMode.DISABLED,
        index=True,
        comment="消息保存模式，默认DISABLED，定义该群组的消息保存策略",
    )

    save_start_date: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True, comment="保存开始时间，可选字段，从什么时间开始保存消息"
    )

    save_end_date: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True, comment="保存结束时间，可选字段，到什么时间停止保存消息"
    )

    max_messages_per_day: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="每日最大消息数，可选字段，限制每天保存的消息数量，0表示无限制"
    )

    max_file_size_mb: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="最大文件大小(MB)，可选字段，限制保存的文件大小，0表示无限制"
    )

    # ==================== 过滤配置字段 ====================

    save_text_messages: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="保存文本消息，默认True，是否保存文本类型的消息"
    )

    save_media_messages: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="保存媒体消息，默认True，是否保存图片、视频等媒体消息"
    )

    save_forwarded_messages: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="保存转发消息，默认True，是否保存转发的消息"
    )

    save_reply_messages: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="保存回复消息，默认True，是否保存回复其他消息的消息"
    )

    save_bot_messages: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="保存机器人消息，默认True，是否保存机器人发送的消息"
    )

    # ==================== 关键词过滤字段 ====================

    include_keywords: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="包含关键词，可选字段，JSON格式存储，只保存包含这些关键词的消息"
    )

    exclude_keywords: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="排除关键词，可选字段，JSON格式存储，不保存包含这些关键词的消息"
    )

    # ==================== 统计字段 ====================

    total_messages_saved: Mapped[int] = mapped_column(
        Integer, default=0, comment="已保存消息总数，默认0，该群组已保存的消息数量统计"
    )

    last_message_date: Mapped[datetime.datetime | None] = mapped_column(
        nullable=True, comment="最后消息时间，可选字段，该群组最后一条保存消息的时间"
    )

    # ==================== 管理字段 ====================

    configured_by_user_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="配置者用户ID，可选字段，配置该群组设置的管理员用户ID"
    )

    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="备注信息，可选字段，关于该群组配置的备注说明"
    )

    # ==================== 数据库索引配置 ====================

    __table_args__ = (
        # 基础查询索引
        Index("idx_group_configs_chat_id", "chat_id"),  # 聊天ID索引，用于快速查找群组配置
        Index("idx_group_configs_enabled", "is_message_save_enabled"),  # 启用状态索引，用于查询启用消息保存的群组
        Index("idx_group_configs_mode", "message_save_mode"),  # 保存模式索引，用于按保存模式分组查询
        Index("idx_group_configs_type", "group_type"),  # 群组类型索引，用于按群组类型查询
        # 时间范围索引
        Index("idx_group_configs_save_dates", "save_start_date", "save_end_date"),  # 保存时间范围索引
        Index("idx_group_configs_last_message", "last_message_date"),  # 最后消息时间索引
        # 组合索引
        Index("idx_group_configs_enabled_type", "is_message_save_enabled", "group_type"),  # 启用状态和群组类型组合索引
        Index("idx_group_configs_username", "chat_username"),  # 用户名索引，用于通过用户名查找群组
        # 统计索引
        Index("idx_group_configs_stats", "total_messages_saved", "last_message_date"),  # 统计信息索引
    )

    # ==================== 模型展示配置 ====================

    repr_cols = ("id", "chat_id", "chat_title", "group_type", "is_message_save_enabled", "message_save_mode")

    # ==================== 实例方法 ====================

    def is_save_enabled(self) -> bool:
        """
        检查是否启用消息保存

        Returns:
            bool: True表示启用，False表示禁用
        """
        return self.is_message_save_enabled and self.message_save_mode != MessageSaveMode.DISABLED

    def is_in_save_period(self, check_time: datetime.datetime | None = None) -> bool:
        """
        检查指定时间是否在保存时间范围内

        Args:
            check_time: 要检查的时间，默认为当前时间

        Returns:
            bool: True表示在保存时间范围内
        """
        if check_time is None:
            check_time = datetime.datetime.now()

        # 检查开始时间
        if self.save_start_date and check_time < self.save_start_date:
            return False

        # 检查结束时间
        return not (self.save_end_date and check_time > self.save_end_date)

    def should_save_message(
        self, message_type: str, is_forwarded: bool = False, is_reply: bool = False, is_from_bot: bool = False
    ) -> bool:
        """
        判断是否应该保存指定类型的消息

        Args:
            message_type: 消息类型
            is_forwarded: 是否为转发消息
            is_reply: 是否为回复消息
            is_from_bot: 是否来自机器人

        Returns:
            bool: True表示应该保存
        """
        # 检查基本启用状态
        if not self.is_save_enabled():
            return False

        # 检查时间范围
        if not self.is_in_save_period():
            return False

        # 检查机器人消息
        if is_from_bot and not self.save_bot_messages:
            return False

        # 检查转发消息
        if is_forwarded and not self.save_forwarded_messages:
            return False

        # 检查回复消息
        if is_reply and not self.save_reply_messages:
            return False

        # 根据保存模式检查消息类型
        if self.message_save_mode == MessageSaveMode.ALL:
            return True
        if self.message_save_mode == MessageSaveMode.TEXT_ONLY:
            return message_type == "text" and self.save_text_messages
        if self.message_save_mode == MessageSaveMode.MEDIA_ONLY:
            return message_type != "text" and self.save_media_messages
        if self.message_save_mode == MessageSaveMode.IMPORTANT_ONLY:
            return is_reply or is_forwarded  # 回复和转发被认为是重要消息

        return False

    def increment_message_count(self, message_date: datetime.datetime | None = None) -> None:
        """
        增加消息计数

        Args:
            message_date: 消息时间，默认为当前时间
        """
        self.total_messages_saved += 1
        if message_date:
            self.last_message_date = message_date
        else:
            self.last_message_date = datetime.datetime.now()

    def get_save_status_display(self) -> str:
        """
        获取保存状态的显示文本

        Returns:
            str: 保存状态的中文描述
        """
        if not self.is_message_save_enabled:
            return "已禁用"

        mode_display = {
            MessageSaveMode.ALL: "保存所有消息",
            MessageSaveMode.TEXT_ONLY: "仅保存文本",
            MessageSaveMode.MEDIA_ONLY: "仅保存媒体",
            MessageSaveMode.IMPORTANT_ONLY: "仅保存重要消息",
            MessageSaveMode.DISABLED: "已禁用",
        }

        return mode_display.get(self.message_save_mode, "未知模式")

    def get_group_info_display(self) -> str:
        """
        获取群组信息的显示文本

        Returns:
            str: 群组信息的格式化文本
        """
        title = self.chat_title or "未知群组"
        username = f"@{self.chat_username}" if self.chat_username else ""
        return f"{title} {username}".strip()

    # ==================== 类方法 ====================

    @classmethod
    def create_for_group(
        cls,
        chat_id: int,
        chat_title: str | None = None,
        chat_username: str | None = None,
        group_type: GroupType = GroupType.GROUP,
        configured_by_user_id: int | None = None,
        **kwargs,
    ) -> GroupConfigModel:
        """
        为群组创建配置记录

        Args:
            chat_id: 群组聊天ID
            chat_title: 群组标题
            chat_username: 群组用户名
            group_type: 群组类型
            configured_by_user_id: 配置者用户ID
            **kwargs: 其他配置参数

        Returns:
            GroupConfigModel: 创建的群组配置实例
        """
        return cls(
            chat_id=chat_id,
            chat_title=chat_title,
            chat_username=chat_username,
            group_type=group_type,
            configured_by_user_id=configured_by_user_id,
            **kwargs,
        )

    @classmethod
    def enable_message_save(
        cls, chat_id: int, save_mode: MessageSaveMode = MessageSaveMode.ALL, **kwargs
    ) -> GroupConfigModel:
        """
        启用群组消息保存

        Args:
            chat_id: 群组聊天ID
            save_mode: 保存模式
            **kwargs: 其他配置参数

        Returns:
            GroupConfigModel: 配置的群组配置实例
        """
        config = cls.create_for_group(chat_id=chat_id, **kwargs)
        config.is_message_save_enabled = True
        config.message_save_mode = save_mode
        config.save_start_date = datetime.datetime.now()

        return config
