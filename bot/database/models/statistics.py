"""
统计数据模型模块

本模块定义了系统统计数据的数据库模型，
用于存储和管理各种业务指标和性能数据。

作者: Telegram Bot Template
创建时间: 2024-01-23
最后更新: 2025-10-21
"""

from __future__ import annotations
import json
from enum import Enum
from typing import TYPE_CHECKING, Any
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, Float, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin

if TYPE_CHECKING:
    pass


class StatisticType(str, Enum):
    """
    统计类型枚举

    定义了系统支持的各种统计指标类型，
    用于分类和管理不同维度的统计数据。
    """

    # ==================== 用户相关统计 ====================
    DAILY_USERS = "daily_users"                    # 日活跃用户数统计
    DAILY_NEW_USERS = "daily_new_users"            # 日新增用户数统计
    DAILY_ACTIVE_USERS = "daily_active_users"      # 日活跃用户数统计
    WEEKLY_USERS = "weekly_users"                  # 周活跃用户数统计
    WEEKLY_NEW_USERS = "weekly_new_users"          # 周新增用户数统计
    MONTHLY_USERS = "monthly_users"                # 月活跃用户数统计
    MONTHLY_NEW_USERS = "monthly_new_users"        # 月新增用户数统计
    USER_RETENTION = "user_retention"              # 用户留存率统计
    USER_CHURN = "user_churn"                      # 用户流失率统计

    # ==================== 消息相关统计 ====================
    DAILY_MESSAGES = "daily_messages"              # 日消息数量统计
    WEEKLY_MESSAGES = "weekly_messages"            # 周消息数量统计
    MONTHLY_MESSAGES = "monthly_messages"          # 月消息数量统计
    MESSAGE_TYPE_DISTRIBUTION = "message_type_distribution"  # 消息类型分布统计
    AVERAGE_MESSAGE_LENGTH = "average_message_length"        # 平均消息长度统计

    # ==================== 功能使用统计 ====================
    COMMAND_USAGE = "command_usage"                # 命令使用次数统计
    FEATURE_USAGE = "feature_usage"                # 功能使用次数统计
    BUTTON_CLICKS = "button_clicks"                # 按钮点击次数统计
    CALLBACK_USAGE = "callback_usage"              # 回调查询使用统计

    # ==================== 系统性能统计 ====================
    RESPONSE_TIME = "response_time"                # 响应时间统计
    ERROR_COUNT = "error_count"                    # 错误次数统计
    ERROR_RATE = "error_rate"                      # 错误率统计
    API_CALLS = "api_calls"                        # API调用次数统计
    DATABASE_QUERIES = "database_queries"          # 数据库查询次数统计
    MEMORY_USAGE = "memory_usage"                  # 内存使用量统计
    CPU_USAGE = "cpu_usage"                        # CPU使用率统计

    # ==================== 业务指标统计 ====================
    CONVERSION_RATE = "conversion_rate"            # 转化率统计
    ENGAGEMENT_RATE = "engagement_rate"            # 参与度统计
    SESSION_DURATION = "session_duration"          # 会话时长统计
    BOUNCE_RATE = "bounce_rate"                    # 跳出率统计

    # ==================== 内容统计 ====================
    CONTENT_VIEWS = "content_views"                # 内容查看次数统计
    CONTENT_SHARES = "content_shares"              # 内容分享次数统计
    SEARCH_QUERIES = "search_queries"              # 搜索查询次数统计

    # ==================== 自定义统计 ====================
    CUSTOM_METRIC = "custom_metric"                # 自定义指标统计
    BUSINESS_KPI = "business_kpi"                  # 业务关键指标统计
    OTHER = "other"                                # 其他类型统计


class StatisticPeriod(str, Enum):
    """
    统计周期枚举

    定义了统计数据的时间周期类型。
    """

    HOURLY = "hourly"      # 小时级统计
    DAILY = "daily"        # 日级统计
    WEEKLY = "weekly"      # 周级统计
    MONTHLY = "monthly"    # 月级统计
    QUARTERLY = "quarterly"  # 季度级统计
    YEARLY = "yearly"      # 年级统计
    REAL_TIME = "real_time"  # 实时统计


class StatisticsModel(Base, BasicAuditMixin):
    """
    统计数据模型类

    存储系统的各种统计指标和性能数据，
    支持多维度的数据分析和报表生成。

    继承自:
        Base: 基础模型类，提供通用功能
        BasicAuditMixin: 基础审计混入，提供时间戳和软删除功能

    主要功能:
        1. 存储各种类型的统计指标数据
        2. 支持多时间维度的数据聚合
        3. 提供灵活的数据查询和分析接口
        4. 支持自定义统计指标的扩展
        5. 提供数据导出和报表生成功能

    数据库表名: statistics
    """

    __tablename__ = "statistics"

    # ==================== 主键字段 ====================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="统计记录ID，自增主键，唯一标识一条统计记录"
    )

    # ==================== 统计标识字段 ====================

    statistic_type: Mapped[StatisticType] = mapped_column(
        SQLEnum(StatisticType),
        nullable=False,
        index=True,
        comment="统计类型，必填字段，使用StatisticType枚举值标识统计指标的类型"
    )

    period: Mapped[StatisticPeriod] = mapped_column(
        SQLEnum(StatisticPeriod),
        nullable=False,
        default=StatisticPeriod.DAILY,
        index=True,
        comment="统计周期，必填字段，标识统计数据的时间粒度，默认为日级统计"
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="统计日期，必填字段，标识统计数据对应的日期"
    )

    # ==================== 统计维度字段 ====================

    key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="统计键，可选字段，用于细分统计维度，如命令名称、错误类型、用户分组等"
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="统计分类，可选字段，用于对统计指标进行分组管理"
    )

    sub_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="统计子分类，可选字段，用于更细粒度的分类管理"
    )

    # ==================== 统计数值字段 ====================

    value: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        index=True,
        comment="统计值，必填字段，存储统计指标的数值，默认为0"
    )

    float_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="浮点统计值，可选字段，用于存储需要小数精度的统计指标"
    )

    count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="计数值，必填字段，记录统计样本的数量，用于计算平均值等，默认为1"
    )

    min_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="最小值，可选字段，记录统计周期内的最小值"
    )

    max_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="最大值，可选字段，记录统计周期内的最大值"
    )

    sum_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="总和值，可选字段，记录统计周期内的累计值"
    )

    # ==================== 扩展数据字段 ====================

    extra_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="扩展数据，可选字段，JSON格式存储额外的统计元数据和详细信息"
    )

    tags: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="标签，可选字段，逗号分隔的标签列表，用于统计数据的标记和搜索"
    )

    # ==================== 时间范围字段 ====================

    start_time: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="开始时间，可选字段，统计周期的开始时间，用于精确的时间范围统计"
    )

    end_time: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="结束时间，可选字段，统计周期的结束时间，用于精确的时间范围统计"
    )

    # ==================== 状态字段 ====================

    is_processed: Mapped[bool] = mapped_column(
        default=True,
        index=True,
        comment="是否已处理，默认True，False表示统计数据还在处理中"
    )

    is_aggregated: Mapped[bool] = mapped_column(
        default=False,
        comment="是否已聚合，默认False，True表示此数据是由其他数据聚合而来"
    )

    # ==================== 数据库索引定义 ====================

    __table_args__ = (
        # 类型日期索引，用于按类型和日期查询统计数据
        Index("idx_statistics_type_date", "statistic_type", "date"),

        # 类型键日期索引，用于细分维度查询
        Index("idx_statistics_type_key_date", "statistic_type", "key", "date"),

        # 周期日期索引，用于按周期查询
        Index("idx_statistics_period_date", "period", "date"),

        # 分类索引，用于按分类查询
        Index("idx_statistics_category", "category", "sub_category"),

        # 数值索引，用于按数值范围查询
        Index("idx_statistics_value", "value", "float_value"),

        # 时间范围索引，用于精确时间查询
        Index("idx_statistics_time_range", "start_time", "end_time"),

        # 处理状态索引，用于查询待处理数据
        Index("idx_statistics_processed", "is_processed", "is_aggregated"),

        # 组合查询索引，用于复杂查询优化
        Index("idx_statistics_complex", "statistic_type", "period", "category", "date"),

        # 软删除相关索引（继承自BasicAuditMixin）
        Index("idx_statistics_deleted", "is_deleted"),
        Index("idx_statistics_updated", "updated_at"),
    )

    # ==================== 显示配置 ====================

    # 用于__repr__方法显示的关键列
    repr_cols = ("id", "statistic_type", "period", "date", "key", "value", "is_deleted")

    # ==================== 业务方法 ====================

    def get_average_value(self) -> float:
        """
        获取平均值

        根据总和值和计数计算平均值。

        返回:
            float: 平均值，如果计数为0则返回0
        """
        if self.count == 0:
            return 0.0

        if self.sum_value is not None:
            return self.sum_value / self.count
        if self.float_value is not None:
            return self.float_value
        return float(self.value) / self.count

    def get_display_value(self) -> str:
        """
        获取用于显示的统计值

        返回适合在界面中显示的格式化统计值。

        返回:
            str: 格式化的显示值
        """
        if self.float_value is not None:
            return f"{self.float_value:.2f}"
        return f"{self.value:,}"

    def get_extra_data_dict(self) -> dict[str, Any]:
        """
        获取扩展数据字典

        将JSON格式的扩展数据转换为Python字典。

        返回:
            Dict[str, Any]: 扩展数据字典，如果解析失败则返回空字典
        """
        if not self.extra_data:
            return {}

        try:
            return json.loads(self.extra_data)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_extra_data_dict(self, data: dict[str, Any]) -> None:
        """
        设置扩展数据字典

        将Python字典转换为JSON格式存储。

        参数:
            data: 要存储的数据字典
        """
        if data:
            self.extra_data = json.dumps(data, ensure_ascii=False)
        else:
            self.extra_data = None

    def get_tags_list(self) -> list[str]:
        """
        获取标签列表

        将逗号分隔的标签字符串转换为列表。

        返回:
            List[str]: 标签列表
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    def set_tags_list(self, tags: list[str]) -> None:
        """
        设置标签列表

        将标签列表转换为逗号分隔的字符串。

        参数:
            tags: 标签列表
        """
        self.tags = ",".join(tags) if tags else None

    def update_value(self, new_value: float, increment: bool = False) -> None:
        """
        更新统计值

        更新统计值并重新计算相关的聚合数据。

        参数:
            new_value: 新的统计值
            increment: 是否为增量更新，True表示累加，False表示替换
        """
        if increment:
            if self.float_value is not None:
                self.float_value += new_value
            else:
                self.value += int(new_value)

            # 更新聚合数据
            if self.sum_value is not None:
                self.sum_value += new_value
            else:
                self.sum_value = float(self.value)

            self.count += 1

            # 更新最值
            if self.min_value is None or new_value < self.min_value:
                self.min_value = new_value
            if self.max_value is None or new_value > self.max_value:
                self.max_value = new_value
        elif isinstance(new_value, float):
            self.float_value = new_value
            self.value = int(new_value)
        else:
            self.value = int(new_value)
            self.float_value = None

    def get_period_display(self) -> str:
        """
        获取统计周期的显示名称

        返回:
            str: 周期显示名称
        """
        period_names = {
            StatisticPeriod.HOURLY: "小时",
            StatisticPeriod.DAILY: "日",
            StatisticPeriod.WEEKLY: "周",
            StatisticPeriod.MONTHLY: "月",
            StatisticPeriod.QUARTERLY: "季度",
            StatisticPeriod.YEARLY: "年",
            StatisticPeriod.REAL_TIME: "实时"
        }
        return period_names.get(self.period, "未知")

    def get_type_display(self) -> str:
        """
        获取统计类型的显示名称

        返回:
            str: 类型显示名称
        """
        type_names = {
            StatisticType.DAILY_USERS: "日活跃用户",
            StatisticType.DAILY_NEW_USERS: "日新增用户",
            StatisticType.DAILY_MESSAGES: "日消息数量",
            StatisticType.COMMAND_USAGE: "命令使用",
            StatisticType.ERROR_COUNT: "错误次数",
            StatisticType.RESPONSE_TIME: "响应时间",
            StatisticType.CONVERSION_RATE: "转化率",
            StatisticType.ENGAGEMENT_RATE: "参与度",
            # 可以继续添加更多类型的显示名称
        }
        return type_names.get(self.statistic_type, self.statistic_type.value)

    def is_performance_metric(self) -> bool:
        """
        判断是否为性能指标

        返回:
            bool: True表示是性能指标，False表示不是
        """
        performance_types = {
            StatisticType.RESPONSE_TIME,
            StatisticType.ERROR_COUNT,
            StatisticType.ERROR_RATE,
            StatisticType.API_CALLS,
            StatisticType.DATABASE_QUERIES,
            StatisticType.MEMORY_USAGE,
            StatisticType.CPU_USAGE
        }
        return self.statistic_type in performance_types

    def is_business_metric(self) -> bool:
        """
        判断是否为业务指标

        返回:
            bool: True表示是业务指标，False表示不是
        """
        business_types = {
            StatisticType.CONVERSION_RATE,
            StatisticType.ENGAGEMENT_RATE,
            StatisticType.USER_RETENTION,
            StatisticType.USER_CHURN,
            StatisticType.BOUNCE_RATE,
            StatisticType.BUSINESS_KPI
        }
        return self.statistic_type in business_types

    @classmethod
    def create_statistic(
        cls,
        statistic_type: StatisticType,
        date: date,
        value: float,
        key: str | None = None,
        period: StatisticPeriod = StatisticPeriod.DAILY,
        category: str | None = None,
        extra_data: dict[str, Any] | None = None,
        **kwargs
    ) -> StatisticsModel:
        """
        创建统计记录

        便捷方法用于创建新的统计记录。

        参数:
            statistic_type: 统计类型
            date: 统计日期
            value: 统计值
            key: 统计键，可选
            period: 统计周期，默认为日级
            category: 统计分类，可选
            extra_data: 扩展数据，可选
            **kwargs: 其他字段参数

        返回:
            StatisticsModel: 新创建的统计实例
        """
        statistic = cls(
            statistic_type=statistic_type,
            date=date,
            key=key,
            period=period,
            category=category,
            **kwargs
        )

        # 设置统计值
        statistic.update_value(value)

        # 设置扩展数据
        if extra_data:
            statistic.set_extra_data_dict(extra_data)

        return statistic
