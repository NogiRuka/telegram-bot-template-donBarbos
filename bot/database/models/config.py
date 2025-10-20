from __future__ import annotations
from enum import Enum

from sqlalchemy import String, Text, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, created_at, updated_at


class ConfigType(str, Enum):
    """配置类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    TEXT = "text"


class ConfigModel(Base):
    """
    系统配置模型类，用于存储动态配置信息
    
    字段说明：
    - key: 配置键（主键）
    - value: 配置值
    - config_type: 配置类型
    - description: 配置描述
    - category: 配置分类
    - is_public: 是否为公开配置
    - is_editable: 是否可编辑
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    __tablename__ = "configs"

    # 主键
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    
    # 配置信息
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_type: Mapped[ConfigType] = mapped_column(SQLEnum(ConfigType), nullable=False, default=ConfigType.STRING)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    
    # 权限控制
    is_public: Mapped[bool] = mapped_column(default=False, index=True)
    is_editable: Mapped[bool] = mapped_column(default=True, index=True)
    
    # 时间戳
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]
    
    # 索引定义
    __table_args__ = (
        Index('idx_configs_category', 'category'),
        Index('idx_configs_type', 'config_type'),
        Index('idx_configs_public_editable', 'is_public', 'is_editable'),
    )
    
    # 用于repr显示的列
    repr_cols = ('key', 'config_type', 'category', 'is_public')