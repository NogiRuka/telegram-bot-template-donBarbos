"""Emby 客户端工具模块

功能说明:
- 提供全局的 Emby 客户端实例获取
- 统一管理 Emby 客户端配置和构建
"""

from __future__ import annotations

from bot.core.config import settings
from bot.core.emby import EmbyClient

_emby_client: EmbyClient | None = None

def get_emby_client() -> EmbyClient | None:
    global _emby_client

    if _emby_client is not None:
        return _emby_client

    base_url = settings.get_emby_base_url()
    api_key = settings.get_emby_api_key()

    if not base_url or not api_key:
        return None

    _emby_client = EmbyClient(
        base_url, 
        api_key,
    )

    return _emby_client
