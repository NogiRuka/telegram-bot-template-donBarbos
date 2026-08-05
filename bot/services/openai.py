"""OpenAI API 客户端。"""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from bot.utils.http import HttpClient
from bot.services.openai_usage import usage_tracker


class OpenAIClient:
    """封装 OpenAI 组织成本接口。"""

    def __init__(self, api_key: str, base_url: str) -> None:
        """创建 OpenAI 客户端。"""
        self._client = HttpClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        """关闭底层 HTTP 会话。"""
        await self._client.close()

    async def get_costs(self, params: dict[str, Any]) -> dict[str, Any]:
        """请求 OpenAI 组织成本数据。"""
        try:
            response = await self._client.request("GET", "/organization/costs", params=params)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            raise
        if not isinstance(response, dict):
            msg = "OpenAI 成本接口返回了非 JSON 对象"
            raise TypeError(msg)
        return response

    async def request(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """发送 OpenAI JSON 请求并自动记录响应 usage。"""
        try:
            response = await self._client.request("POST", endpoint, json=payload)
        except (aiohttp.ClientError, asyncio.TimeoutError):
            raise
        if not isinstance(response, dict):
            msg = "OpenAI 接口返回了非 JSON 对象"
            raise TypeError(msg)
        await usage_tracker.record(endpoint, response)
        return response
