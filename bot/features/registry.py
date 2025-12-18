"""
功能注册核心模块
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, List, Tuple
from aiogram.types import InlineKeyboardButton
from bot.config import USER_FEATURES_MAPPING

@dataclass
class UserFeature:
    """用户功能定义"""
    name: str                    # 功能名称 (如: user.demo)
    label: str                   # 显示标签
    description: str = ""        # 功能描述
    handler: Optional[Callable] = None  # 处理函数
    callback_data: Optional[str] = None # 回调数据 (自动生成)
    config_key: Optional[str] = None      # 配置键 (自动生成)
    enabled: bool = True                 # 默认启用状态
    show_in_panel: bool = True           # 是否在面板显示
    button_order: int = 100              # 按钮排序

    def __post_init__(self):
        # 自动生成 callback_data
        if not self.callback_data:
            self.callback_data = self.name.replace(".", ":")
        # 自动生成 config_key
        if not self.config_key:
            self.config_key = self.name.replace(".", "_")

    @property
    def filter(self):
        """获取 aiogram 过滤器"""
        from aiogram import F
        return F.data == self.callback_data

    @property
    def require(self):
        """获取权限装饰器"""
        from bot.utils.permissions import require_user_feature
        return require_user_feature(self.name)

    def create_router(self):
        """创建专用路由器"""
        from aiogram import Router
        return Router(name=self.config_key)

    @property
    def button(self) -> InlineKeyboardButton:
        """获取内联按钮"""
        return InlineKeyboardButton(text=self.label, callback_data=self.callback_data)


class FeatureRegistry:
    """功能注册器"""
    def __init__(self):
        self._features: Dict[str, UserFeature] = {}
        self._buttons: Dict[str, InlineKeyboardButton] = {}

    def register(self, feature: UserFeature) -> UserFeature:
        """注册功能"""
        self._features[feature.name] = feature
        self._buttons[feature.name] = feature.button
        
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
        from bot.utils.text import format_with_status
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
