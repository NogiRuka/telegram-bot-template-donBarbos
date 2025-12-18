"""
功能注册系统

功能说明:
- 统一管理所有用户功能
- 自动生成按钮、处理器、路由
- 支持功能开关和权限控制
- 实现"只改一个地方"的开发目标

使用示例:
    # 注册新功能
    register_user_feature(
        name="user.demo",
        label="演示功能",
        description="这是一个演示功能",
        handler=handle_demo_feature,
        enabled=True
    )
"""

from typing import Callable, Optional
from dataclasses import dataclass
from aiogram.types import InlineKeyboardButton
from bot.utils.permissions import require_user_feature
from bot.config.mappings import USER_FEATURES_MAPPING
from bot.keyboards.inline.labels import format_with_status


@dataclass
class UserFeature:
    """用户功能定义"""
    
    # 基础信息
    name: str                    # 功能名称 (如: user.demo)
    label: str                   # 显示标签
    description: str = ""        # 功能描述
    
    # 处理器
    handler: Optional[Callable] = None  # 处理函数
    callback_data: Optional[str] = None # 回调数据 (自动生成)
    
    # 配置
    config_key: Optional[str] = None      # 配置键 (自动生成)
    enabled: bool = True                 # 默认启用状态
    
    # UI 设置
    show_in_panel: bool = True           # 是否在面板显示
    button_order: int = 100              # 按钮排序
    
    def __post_init__(self):
        """自动生成缺失字段"""
        if not self.callback_data:
            self.callback_data = self.name.replace(".", ":")
        
        if not self.config_key:
            self.config_key = self.name.replace(".", "_")


class FeatureRegistry:
    """功能注册器"""
    
    def __init__(self):
        self._features: dict[str, UserFeature] = {}
        self._buttons: dict[str, InlineKeyboardButton] = {}
    
    def register(self, feature: UserFeature) -> UserFeature:
        """注册功能"""
        self._features[feature.name] = feature
        
        # 自动生成按钮
        button = InlineKeyboardButton(
            text=feature.label,
            callback_data=feature.callback_data
        )
        self._buttons[feature.name] = button
        
        # 更新功能映射
        USER_FEATURES_MAPPING[feature.config_key] = (feature.config_key, feature.label)
        
        return feature
    
    def get_feature(self, name: str) -> Optional[UserFeature]:
        """获取功能定义"""
        return self._features.get(name)
    
    def get_button(self, name: str) -> Optional[InlineKeyboardButton]:
        """获取功能按钮"""
        return self._buttons.get(name)
    
    def get_all_buttons(self, enabled_features: dict[str, bool] = None) -> list[InlineKeyboardButton]:
        """获取所有启用的功能按钮"""
        buttons = []
        
        # 按排序获取功能
        sorted_features = sorted(
            [f for f in self._features.values() if f.show_in_panel],
            key=lambda x: x.button_order
        )
        
        for feature in sorted_features:
            if enabled_features:
                # 添加状态显示
                is_enabled = enabled_features.get(feature.config_key, feature.enabled)
                text = format_with_status(feature.label, is_enabled)
            else:
                text = feature.label
            
            button = InlineKeyboardButton(
                text=text,
                callback_data=feature.callback_data
            )
            buttons.append(button)
        
        return buttons
    
    def create_decorator(self, feature_name: str):
        """创建功能装饰器"""
        return require_user_feature(feature_name)
    
    def get_handler_routes(self) -> list[tuple[str, Callable]]:
        """获取所有处理器路由"""
        routes = []
        for feature in self._features.values():
            if feature.handler:
                routes.append((feature.callback_data, feature.handler))
        return routes


# 全局注册器实例
feature_registry = FeatureRegistry()


def register_user_feature(
    name: str,
    label: str,
    description: str = "",
    handler: Optional[Callable] = None,
    callback_data: Optional[str] = None,
    config_key: Optional[str] = None,
    enabled: bool = True,
    show_in_panel: bool = True,
    button_order: int = 100
) -> UserFeature:
    """
    注册用户功能
    
    功能说明:
    - 简化功能注册流程
    - 自动生成按钮和配置
    - 支持权限控制
    
    输入参数:
    - name: 功能名称 (如: user.demo)
    - label: 显示标签
    - description: 功能描述
    - handler: 处理函数
    - callback_data: 回调数据 (可选，自动生成)
    - config_key: 配置键 (可选，自动生成)
    - enabled: 默认启用状态
    - show_in_panel: 是否在面板显示
    - button_order: 按钮排序
    
    返回值:
    - UserFeature: 功能定义对象
    """
    feature = UserFeature(
        name=name,
        label=label,
        description=description,
        handler=handler,
        callback_data=callback_data,
        config_key=config_key,
        enabled=enabled,
        show_in_panel=show_in_panel,
        button_order=button_order
    )
    
    return feature_registry.register(feature)


def get_user_feature_button(name: str) -> Optional[InlineKeyboardButton]:
    """获取用户功能按钮"""
    return feature_registry.get_button(name)


def get_all_user_feature_buttons(enabled_features: dict[str, bool] = None) -> list[InlineKeyboardButton]:
    """获取所有用户功能按钮"""
    return feature_registry.get_all_buttons(enabled_features)