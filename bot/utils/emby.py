"""Emby 客户端工具模块

功能说明:
- 提供全局的 Emby 客户端实例获取
- 统一管理 Emby 客户端配置和构建
"""

from __future__ import annotations

from bot.core.config import settings
from bot.core.emby import EmbyClient


def get_emby_client() -> EmbyClient | None:
    """获取 Emby 客户端实例

    功能说明:
    - 从配置中构建 EmbyClient 实例
    - 任一配置缺失返回 None
    - 用于全局统一的 Emby 客户端获取

    输入参数:
    - 无

    返回值:
    - EmbyClient | None: 客户端实例或 None（配置缺失时）
    """
    base_url = settings.get_emby_base_url()
    api_key = settings.get_emby_api_key()
    if not base_url or not api_key:
        return None
    return EmbyClient(base_url, api_key)
