from __future__ import annotations
import datetime
from enum import Enum

from sqlalchemy import String, Index, BigInteger, Enum as SQLEnum, Date
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, created_at, updated_at


class StatisticType(str, Enum):
    """统计类型枚举"""
    DAILY_USERS = "daily_users"
    DAILY_MESSAGES = "daily_messages"
    DAILY_NEW_USERS = "daily_new_users"
    DAILY_ACTIVE_USERS = "daily_active_users"
    WEEKLY_USERS = "weekly_users"
    WEEKLY_MESSAGES = "weekly_messages"
    MONTHLY_USERS = "monthly_users"
    MONTHLY_MESSAGES = "monthly_messages"
    COMMAND_USAGE = "command_usage"
    ERROR_COUNT = "error_count"
    PERFORMANCE_METRIC = "performance_metric"


class StatisticsModel(Base):
    """
    统计数据模型类，用于存储各种统计信息
    
    字段说明：
    - id: 统计ID（自增主键）
    - statistic_type: 统计类型
    - date: 统计日期
    - key: 统计键（如命令名称、错误类型等）
    - value: 统计值
    - extra_data: 额外元数据
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    __tablename__ = "statistics"

    # 主键（自增）
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 统计信息
    statistic_type: Mapped[StatisticType] = mapped_column(SQLEnum(StatisticType), nullable=False, index=True)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True)
    key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    extra_data: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    # 时间戳
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
    
    # 索引定义
    __table_args__ = (
        Index('idx_statistics_type_date', 'statistic_type', 'date'),
        Index('idx_statistics_type_key_date', 'statistic_type', 'key', 'date'),
        Index('idx_statistics_date', 'date'),
    )
    
    # 用于repr显示的列
    repr_cols = ('id', 'statistic_type', 'date', 'key', 'value')