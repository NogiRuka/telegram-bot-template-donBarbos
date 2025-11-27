"""配置模型"""

from __future__ import annotations
import json
from enum import Enum
from typing import Any

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class ConfigType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    TEXT = "text"
    LIST = "list"
    DICT = "dict"


class ConfigModel(Base, BasicAuditMixin):

    __tablename__ = "configs"

    # ==================== 主键字段 ====================

    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="配置键名, 主键, 唯一标识配置项, 建议使用点分隔层级结构"
    )

    # ==================== 配置内容 ====================

    value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="配置值, 可选字段, 以字符串形式存储, 实际类型由 config_type 字段决定"
    )

    config_type: Mapped[ConfigType] = mapped_column(
        SQLEnum(ConfigType),
        nullable=False,
        default=ConfigType.STRING,
        index=True,
        comment="配置类型, 必填字段, 使用 ConfigType 枚举值, 用于值的类型验证和转换"
    )


    # ==================== 描述信息 ====================


    # ==================== 权限控制 ====================


    # ==================== 验证规则 ====================


    # ==================== 元数据信息 ====================


    # ==================== 数据库索引定义 ====================

    __table_args__ = (
        Index("idx_configs_type", "config_type"),
        Index("idx_configs_deleted", "is_deleted"),
        Index("idx_configs_updated", "updated_at"),
    )

    # ==================== 显示配置 ====================

    # 用于__repr__方法显示的关键列
    repr_cols = ("key", "config_type", "is_deleted")

    # ==================== 业务方法 ====================

    def get_typed_value(self) -> Any:
        """
        获取类型化的配置值

        功能说明:
        - 根据 `config_type` 将字符串值转换为对应的 Python 类型

        输入参数:
        - 无

        返回值:
        - Any: 转换后的配置值, 类型由 `config_type` 决定
        """
        if self.value is None:
            defaults: dict[ConfigType, Any] = {
                ConfigType.STRING: "",
                ConfigType.TEXT: "",
                ConfigType.INTEGER: 0,
                ConfigType.FLOAT: 0.0,
                ConfigType.BOOLEAN: False,
                ConfigType.JSON: {},
                ConfigType.LIST: [],
                ConfigType.DICT: {},
            }
            return defaults.get(self.config_type, None)

        converters: dict[ConfigType, Any] = {
            ConfigType.STRING: lambda v: v,
            ConfigType.TEXT: lambda v: v,
            ConfigType.INTEGER: lambda v: int(v),
            ConfigType.FLOAT: lambda v: float(v),
            ConfigType.BOOLEAN: lambda v: str(v).lower() in ("true", "1", "yes", "on"),
            ConfigType.JSON: lambda v: json.loads(v) if v else {},
            ConfigType.LIST: lambda v: json.loads(v) if v else [],
            ConfigType.DICT: lambda v: json.loads(v) if v else {},
        }
        try:
            fn = converters.get(self.config_type, lambda v: v)
            return fn(self.value)
        except (ValueError, json.JSONDecodeError) as e:
            msg = f"无法将配置值 '{self.value}' 转换为类型 {self.config_type.value}: {e}"
            raise ValueError(msg) from e

    # 已移除默认值支持

    def set_typed_value(self, value: Any) -> None:
        """
        设置类型化的配置值

        将Python值转换为字符串格式存储到value字段。

        参数:
            value: 要设置的值, 类型应与 config_type 匹配

        异常:
            ValueError: 当值类型不匹配时抛出
        """
        if value is None:
            self.value = None
            return

        try:
            if self.config_type in (ConfigType.STRING, ConfigType.TEXT):
                self.value = str(value)
            elif self.config_type == ConfigType.INTEGER:
                self.value = str(int(value))
            elif self.config_type == ConfigType.FLOAT:
                self.value = str(float(value))
            elif self.config_type == ConfigType.BOOLEAN:
                self.value = str(bool(value)).lower()
            elif self.config_type in (ConfigType.JSON, ConfigType.LIST, ConfigType.DICT):
                self.value = json.dumps(value, ensure_ascii=False)
            else:
                self.value = str(value)
        except (ValueError, TypeError) as e:
            msg = f"无法将值 '{value}' 转换为配置类型 {self.config_type.value}: {e}"
            raise ValueError(msg) from e

    # 已移除验证规则相关方法

    # 已移除显示值相关方法

    # 已移除标签相关方法

    # 已移除权限相关方法

    # 已移除权限相关方法

    # 已移除创建配置便捷方法
