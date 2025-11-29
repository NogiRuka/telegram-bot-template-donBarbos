from __future__ import annotations
import asyncio
from typing import Any

import aiohttp


class HttpClient:
    """HTTP 客户端

    功能说明:
    - 为 Emby 等外部服务提供统一的异步请求封装, 自动携带令牌头

    输入参数:
    - base_url: 服务基础地址, 如 `https://your-emby.com`
    - token: 访问令牌, 写入 `X-Emby-Token` 请求头, 可为 None

    返回值:
    - 无

    依赖安装:
    - pip install aiohttp[speedups]
    """

    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    async def request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """发送 HTTP 请求

        功能说明:
        - 统一拼接 `base_url + endpoint`, 注入 `X-Emby-Token` 头, 使用 15s 超时

        输入参数:
        - method: HTTP 方法, 如 `GET`/`POST`/`DELETE`
        - endpoint: 路径, 以 `/` 开头, 如 `/Users`
        - **kwargs: 透传给 `aiohttp.ClientSession.request` 的参数, 如 `json`, `params`

        返回值:
        - Any: 解析后的响应体, 优先尝试 `JSON`, 失败回退为文本

        错误处理:
        - 网络错误或非 2xx 状态将抛出异常, 调用方需 `try/except`

        Telegram API 说明:
        - 本函数与 Telegram API 无直接交互, 仅为外部服务调用工具
        """
        headers: dict[str, str] = dict(kwargs.pop("headers", {}) or {})
        if self.token:
            headers["X-Emby-Token"] = self.token

        timeout = aiohttp.ClientTimeout(total=15)
        url = f"{self.base_url}{endpoint}"
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method=method.upper(), url=url, headers=headers, **kwargs) as resp:
                resp.raise_for_status()
                ctype = resp.headers.get("Content-Type", "")
                if "application/json" in ctype:
                    return await resp.json()
                return await resp.text()

