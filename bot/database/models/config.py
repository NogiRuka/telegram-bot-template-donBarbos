"""配置模型定义"""

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

    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="配置键名"
    )

    value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="配置值字符串表示, 类型由 config_type 决定"
    )

    config_type: Mapped[ConfigType] = mapped_column(
        SQLEnum(ConfigType),
        nullable=False,
        default=ConfigType.STRING,
        index=True,
        comment="配置值类型"
    )

    __table_args__ = (
        Index("idx_configs_type", "config_type"),
        Index("idx_configs_deleted", "is_deleted"),
        Index("idx_configs_updated", "updated_at"),
    )

    repr_cols = ("key", "config_type", "is_deleted")

    def get_typed_value(self) -> Any:
        """获取类型化配置值

        功能说明:
        - 按 `config_type` 将字符串值转换为对应类型

        输入参数:
        - 无

        返回值:
        - Any: 转换后的配置值; 当 `value` 为 None 时返回类型默认值
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

    def set_typed_value(self, value: Any) -> None:
        """设置类型化配置值

        功能说明:
        - 将 Python 值转换为字符串并存储到 `value`

        输入参数:
        - value: 要设置的值

        返回值:
        - None

        异常:
        - ValueError: 当值类型不匹配或转换失败
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
