from __future__ import annotations
import asyncio
import json
from typing import Any

import aiohttp
from loguru import logger


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

    def __init__(self, base_url: str, token: str | None = None, base_path: str | None = None) -> None:
        """初始化 HTTP 客户端

        功能说明:
        - 统一配置基础地址与令牌, 可选配置 `base_path` 作为公共路径前缀(例如 `/emby`)

        输入参数:
        - base_url: 服务基础地址, 如 `https://your-emby.com`
        - token: 访问令牌, 可为 None
        - base_path: 公共路径前缀(可选), 例如 `/emby`

        返回值:
        - None
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        if base_path is None or not base_path.strip():
            self.base_path = ""
        else:
            s = base_path.strip()
            if not s.startswith("/"):
                s = "/" + s
            self.base_path = s.rstrip("/")

    async def request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """发送 HTTP 请求

        功能说明:
        - 统一拼接 `base_url + base_path + endpoint`, 注入 `X-Emby-Token` 头, 使用 15s 超时
        - 始终读取响应体; 对非 2xx 状态抛出异常并附带原始响应体

        输入参数:
        - method: HTTP 方法, 如 `GET`/`POST`/`DELETE`
        - endpoint: 路径, 以 `/` 开头, 如 `/Users`
        - **kwargs: 透传给 `aiohttp.ClientSession.request` 的参数, 如 `json`, `params`

        返回值:
        - Any: 解析后的响应体, 优先尝试 `JSON`, 失败回退为文本
        """
        headers: dict[str, str] = dict(kwargs.pop("headers", {}) or {})
        if self.token:
            headers["X-Emby-Token"] = self.token

        timeout = aiohttp.ClientTimeout(total=15)
        ep = endpoint if endpoint.startswith("/") else "/" + endpoint
        url = f"{self.base_url}{self.base_path}{ep}"
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(method=method.upper(), url=url, headers=headers, **kwargs) as resp:
                    status = resp.status
                    ctype = resp.headers.get("Content-Type", "")
                    text_body = await resp.text()
                    data: Any
                    if "application/json" in ctype:
                        try:
                            data = json.loads(text_body)
                        except Exception:
                            data = text_body
                    else:
                        data = text_body
                    if status >= 400:
                        snippet = (text_body[:1000] + ("…" if len(text_body) > 1000 else "")) if text_body else ""
                        logger.error(
                            "❌ HTTP请求失败: {method} {url} -> {status} {body}",
                            method=method.upper(),
                            url=url,
                            status=status,
                            body=snippet,
                        )
                        raise HttpRequestError(method.upper(), url, status, text_body, dict(resp.headers))
                    return data
        except aiohttp.ClientResponseError as e:
            logger.error(
                "❌ HTTP请求失败: {method} {url} -> {status} {msg}",
                method=method.upper(),
                url=url,
                status=getattr(e, "status", None),
                msg=str(e),
            )
            raise
        except asyncio.TimeoutError as e:
            logger.error(
                "❌ HTTP超时: {method} {url} -> {err}", method=method.upper(), url=url, err=str(e)
            )
            raise
        except aiohttp.ClientError as e:
            logger.error(
                "❌ HTTP网络异常: {method} {url} -> {err}", method=method.upper(), url=url, err=str(e)
            )
            raise


class HttpRequestError(Exception):
    """HTTP 请求错误异常

    功能说明:
    - 封装非 2xx 响应的详细信息, 包含状态码、方法、URL 与原始响应体

    输入参数:
    - method: 请求方法
    - url: 完整请求地址
    - status: 响应状态码
    - body: 原始响应体文本
    - headers: 响应头字典

    返回值:
    - 无
    """

    def __init__(self, method: str, url: str, status: int, body: str, headers: dict[str, str] | None = None) -> None:
        self.method = method
        self.url = url
        self.status = status
        self.body = body
        self.headers = headers or {}
        super().__init__(f"{method} {url} -> {status}")
