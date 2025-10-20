"""
系统配置模型模块

本模块定义了系统动态配置的数据库模型，
用于存储和管理应用程序的各种配置参数。

作者: Telegram Bot Template
创建时间: 2024-01-23
最后更新: 2025-10-21
"""

from __future__ import annotations
from enum import Enum
import json
from typing import Any

from sqlalchemy import String, Text, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base, BasicAuditMixin


class ConfigType(str, Enum):
    """
    配置类型枚举
    
    定义了系统支持的配置值类型，用于类型验证和值转换。
    每种类型都有对应的序列化和反序列化逻辑。
    """
    
    STRING = "string"      # 字符串类型，存储文本配置
    INTEGER = "integer"    # 整数类型，存储数值配置
    FLOAT = "float"        # 浮点数类型，存储小数配置
    BOOLEAN = "boolean"    # 布尔类型，存储开关配置
    JSON = "json"          # JSON类型，存储复杂对象配置
    TEXT = "text"          # 长文本类型，存储大段文本配置
    LIST = "list"          # 列表类型，存储数组配置
    DICT = "dict"          # 字典类型，存储键值对配置


class ConfigModel(Base, BasicAuditMixin):
    """
    系统配置模型类
    
    存储系统的动态配置信息，支持多种数据类型和权限控制。
    配置项可以按分类组织，支持公开/私有、可编辑/只读等权限设置。
    
    继承自:
        Base: 基础模型类，提供通用功能
        BasicAuditMixin: 基础审计混入，提供时间戳和软删除功能
    
    主要功能:
        1. 存储各种类型的配置参数
        2. 支持配置分类和权限控制
        3. 提供类型安全的值存取方法
        4. 支持配置的版本管理和审计
        5. 提供配置的导入导出功能
    
    数据库表名: configs
    """
    
    __tablename__ = "configs"

    # ==================== 主键字段 ====================
    
    key: Mapped[str] = mapped_column(
        String(255), 
        primary_key=True,
        comment="配置键名，作为主键，唯一标识一个配置项，建议使用点分隔的层级结构"
    )
    
    # ==================== 配置内容 ====================
    
    value: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="配置值，可选字段，以字符串形式存储，实际类型由config_type字段决定"
    )
    
    config_type: Mapped[ConfigType] = mapped_column(
        SQLEnum(ConfigType), 
        nullable=False, 
        default=ConfigType.STRING, 
        index=True,
        comment="配置类型，必填字段，使用ConfigType枚举值，用于值的类型验证和转换"
    )
    
    default_value: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="默认值，可选字段，当配置值为空时使用的默认值，格式与value字段相同"
    )
    
    # ==================== 描述信息 ====================
    
    description: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="配置描述，可选字段，详细说明配置项的用途、影响范围和注意事项"
    )
    
    category: Mapped[str | None] = mapped_column(
        String(100), 
        nullable=True, 
        index=True,
        comment="配置分类，可选字段，用于将相关配置项分组管理，如system、bot、ui等"
    )
    
    display_name: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="显示名称，可选字段，用于在管理界面显示的友好名称"
    )
    
    # ==================== 权限控制 ====================
    
    is_public: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="是否公开，默认False，True表示普通用户可以查看此配置项"
    )
    
    is_editable: Mapped[bool] = mapped_column(
        default=True, 
        index=True,
        comment="是否可编辑，默认True，False表示此配置项为只读，不允许修改"
    )
    
    is_system: Mapped[bool] = mapped_column(
        default=False, 
        index=True,
        comment="是否系统配置，默认False，True表示此配置项为系统核心配置，需要特殊权限"
    )
    
    # ==================== 验证规则 ====================
    
    validation_rule: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="验证规则，可选字段，JSON格式存储值的验证规则，如范围、格式、枚举值等"
    )
    
    min_value: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="最小值，可选字段，用于数值类型配置的范围验证"
    )
    
    max_value: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True,
        comment="最大值，可选字段，用于数值类型配置的范围验证"
    )
    
    # ==================== 元数据信息 ====================
    
    tags: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True,
        comment="标签，可选字段，逗号分隔的标签列表，用于配置项的标记和搜索"
    )
    
    sort_order: Mapped[int] = mapped_column(
        default=0,
        comment="排序顺序，默认0，用于在管理界面中控制配置项的显示顺序"
    )
    
    # ==================== 数据库索引定义 ====================
    
    __table_args__ = (
        # 索引定义 - 用于提高查询性能和支持复杂查询
        Index('idx_configs_category', 'category'),  # 配置分类索引，用于按分类查询和管理配置项
        Index('idx_configs_type', 'config_type'),  # 配置类型索引，用于按数据类型查询配置项
        Index('idx_configs_permissions', 'is_public', 'is_editable', 'is_system'),  # 权限组合索引，用于按权限级别过滤配置项
        Index('idx_configs_category_public', 'category', 'is_public'),  # 分类权限索引，用于管理界面按分类和权限查询
        Index('idx_configs_sort', 'category', 'sort_order'),  # 排序索引，用于按分类和排序顺序显示配置项
        Index('idx_configs_deleted', 'is_deleted'),  # 软删除状态索引，用于过滤已删除配置
        Index('idx_configs_updated', 'updated_at'),  # 更新时间索引，用于查询最近修改的配置
    )
    
    # ==================== 显示配置 ====================
    
    # 用于__repr__方法显示的关键列
    repr_cols = ('key', 'config_type', 'category', 'is_public', 'is_deleted')
    
    # ==================== 业务方法 ====================
    
    def get_typed_value(self) -> Any:
        """
        获取类型化的配置值
        
        根据config_type字段将字符串值转换为对应的Python类型。
        
        返回:
            Any: 转换后的配置值，类型由config_type决定
            
        异常:
            ValueError: 当值无法转换为指定类型时抛出
        """
        if self.value is None:
            return self.get_typed_default_value()
        
        try:
            if self.config_type == ConfigType.STRING:
                return self.value
            elif self.config_type == ConfigType.INTEGER:
                return int(self.value)
            elif self.config_type == ConfigType.FLOAT:
                return float(self.value)
            elif self.config_type == ConfigType.BOOLEAN:
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.config_type == ConfigType.JSON:
                return json.loads(self.value)
            elif self.config_type == ConfigType.TEXT:
                return self.value
            elif self.config_type == ConfigType.LIST:
                return json.loads(self.value) if self.value else []
            elif self.config_type == ConfigType.DICT:
                return json.loads(self.value) if self.value else {}
            else:
                return self.value
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"无法将配置值 '{self.value}' 转换为类型 {self.config_type.value}: {e}")
    
    def get_typed_default_value(self) -> Any:
        """
        获取类型化的默认值
        
        根据config_type字段将默认值字符串转换为对应的Python类型。
        
        返回:
            Any: 转换后的默认值，如果没有默认值则返回类型对应的空值
        """
        if self.default_value is None:
            # 返回类型对应的默认空值
            if self.config_type == ConfigType.STRING or self.config_type == ConfigType.TEXT:
                return ""
            elif self.config_type == ConfigType.INTEGER:
                return 0
            elif self.config_type == ConfigType.FLOAT:
                return 0.0
            elif self.config_type == ConfigType.BOOLEAN:
                return False
            elif self.config_type == ConfigType.JSON:
                return None
            elif self.config_type == ConfigType.LIST:
                return []
            elif self.config_type == ConfigType.DICT:
                return {}
            else:
                return None
        
        # 使用临时实例来转换默认值
        temp_config = ConfigModel(
            key=self.key,
            value=self.default_value,
            config_type=self.config_type
        )
        return temp_config.get_typed_value()
    
    def set_typed_value(self, value: Any) -> None:
        """
        设置类型化的配置值
        
        将Python值转换为字符串格式存储到value字段。
        
        参数:
            value: 要设置的值，类型应与config_type匹配
            
        异常:
            ValueError: 当值类型不匹配时抛出
        """
        if value is None:
            self.value = None
            return
        
        try:
            if self.config_type == ConfigType.STRING or self.config_type == ConfigType.TEXT:
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
            raise ValueError(f"无法将值 '{value}' 转换为配置类型 {self.config_type.value}: {e}")
    
    def validate_value(self, value: Any) -> bool:
        """
        验证配置值是否符合规则
        
        根据validation_rule、min_value、max_value等字段验证值的有效性。
        
        参数:
            value: 要验证的值
            
        返回:
            bool: True表示验证通过，False表示验证失败
        """
        try:
            # 类型验证
            if self.config_type == ConfigType.INTEGER:
                value = int(value)
                if self.min_value and value < int(self.min_value):
                    return False
                if self.max_value and value > int(self.max_value):
                    return False
            elif self.config_type == ConfigType.FLOAT:
                value = float(value)
                if self.min_value and value < float(self.min_value):
                    return False
                if self.max_value and value > float(self.max_value):
                    return False
            
            # 自定义验证规则
            if self.validation_rule:
                rule = json.loads(self.validation_rule)
                # 这里可以扩展更复杂的验证逻辑
                if 'enum' in rule and value not in rule['enum']:
                    return False
                if 'pattern' in rule:
                    import re
                    if not re.match(rule['pattern'], str(value)):
                        return False
            
            return True
        except (ValueError, json.JSONDecodeError):
            return False
    
    def get_display_value(self) -> str:
        """
        获取用于显示的配置值
        
        返回适合在界面中显示的格式化值。
        
        返回:
            str: 格式化的显示值
        """
        try:
            typed_value = self.get_typed_value()
            if self.config_type == ConfigType.BOOLEAN:
                return "是" if typed_value else "否"
            elif self.config_type in (ConfigType.JSON, ConfigType.LIST, ConfigType.DICT):
                return json.dumps(typed_value, ensure_ascii=False, indent=2)
            else:
                return str(typed_value)
        except:
            return self.value or ""
    
    def get_tags_list(self) -> list[str]:
        """
        获取标签列表
        
        将逗号分隔的标签字符串转换为列表。
        
        返回:
            list[str]: 标签列表
        """
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def set_tags_list(self, tags: list[str]) -> None:
        """
        设置标签列表
        
        将标签列表转换为逗号分隔的字符串。
        
        参数:
            tags: 标签列表
        """
        self.tags = ','.join(tags) if tags else None
    
    def is_accessible_by_user(self, is_admin: bool = False) -> bool:
        """
        判断用户是否可以访问此配置
        
        根据用户权限和配置的权限设置判断访问权限。
        
        参数:
            is_admin: 是否为管理员用户
            
        返回:
            bool: True表示可以访问，False表示无权访问
        """
        if self.is_deleted:
            return False
        
        if is_admin:
            return True
        
        return self.is_public and not self.is_system
    
    def is_editable_by_user(self, is_admin: bool = False) -> bool:
        """
        判断用户是否可以编辑此配置
        
        根据用户权限和配置的编辑权限判断编辑权限。
        
        参数:
            is_admin: 是否为管理员用户
            
        返回:
            bool: True表示可以编辑，False表示无权编辑
        """
        if not self.is_accessible_by_user(is_admin):
            return False
        
        if not self.is_editable:
            return False
        
        if self.is_system and not is_admin:
            return False
        
        return True
    
    @classmethod
    def create_config(
        cls,
        key: str,
        value: Any,
        config_type: ConfigType = ConfigType.STRING,
        description: str | None = None,
        category: str | None = None,
        is_public: bool = False,
        is_editable: bool = True,
        is_system: bool = False,
        default_value: Any = None,
        **kwargs
    ) -> "ConfigModel":
        """
        创建配置项
        
        便捷方法用于创建新的配置项。
        
        参数:
            key: 配置键名
            value: 配置值
            config_type: 配置类型，默认STRING
            description: 配置描述，可选
            category: 配置分类，可选
            is_public: 是否公开，默认False
            is_editable: 是否可编辑，默认True
            is_system: 是否系统配置，默认False
            default_value: 默认值，可选
            **kwargs: 其他字段参数
            
        返回:
            ConfigModel: 新创建的配置实例
        """
        config = cls(
            key=key,
            config_type=config_type,
            description=description,
            category=category,
            is_public=is_public,
            is_editable=is_editable,
            is_system=is_system,
            **kwargs
        )
        
        # 设置值
        config.set_typed_value(value)
        
        # 设置默认值
        if default_value is not None:
            temp_config = cls(key=key, config_type=config_type)
            temp_config.set_typed_value(default_value)
            config.default_value = temp_config.value
        
        return config