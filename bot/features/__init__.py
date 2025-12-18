"""
功能管理模块

功能说明:
- 统一管理所有功能
- 提供功能注册和查询接口
- 支持功能开关控制
"""

from .registry import (
    register_user_feature,
    get_user_feature_button,
    get_all_user_feature_buttons,
    feature_registry,
    UserFeature,
)

__all__ = [
    "register_user_feature",
    "get_user_feature_button", 
    "get_all_user_feature_buttons",
    "feature_registry",
    "UserFeature",
]