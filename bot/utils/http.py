from __future__ import annotations
import asyncio
import json
from typing import Any

import aiohttp
from loguru import logger


class HttpClient:
    """HTTP 客户端

    功能说明:
    - 提供统一的异步 HTTP 请求封装
    - 支持默认请求头、JSON 自动解析、连接复用
    """

    def __init__(self, base_url: str, headers: dict[str, str] | None = None, base_path: str | None = None) -> None:
        """初始化 HTTP 客户端

        功能说明:
        - 统一配置基础地址与令牌, 可选配置 `base_path` 作为公共路径前缀(例如 `/emby`)

        输入参数:
        - base_url: 服务基础地址, 如 `https://your-emby.com`
        - headers: 请求头, 可为 None
        - base_path: 公共路径前缀(可选), 例如 `/emby`

        返回值:
        - None
        """
        self.base_url = base_url.rstrip("/")
        self.default_headers = headers or {}
        if base_path is None or not base_path.strip():
            self.base_path = ""
        else:
            s = base_path.strip()
            if not s.startswith("/"):
                s = "/" + s
            self.base_path = s.rstrip("/")
        self.session: aiohttp.ClientSession | None = None

    async def close(self) -> None:
        if self.session and not self.session.closed:
            await self.session.close()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                auto_decompress=True,
                headers={
                    "Accept-Encoding": "gzip, deflate",
                    **self.default_headers,
                },
            )
        return self.session

    async def request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """发送 HTTP 请求

        功能说明:
        - 拼接 base_url + base_path + endpoint
        - 合并默认请求头与本次请求头
        - 自动解析 JSON
        - 非 2xx 抛出 HttpRequestError

        输入参数:
        - method: HTTP 方法, 如 `GET`/`POST`/`DELETE`
        - endpoint: 路径, 以 `/` 开头, 如 `/Users`
        - **kwargs: 透传给 `aiohttp.ClientSession.request` 的参数, 如 `json`, `params`

        返回值:
        - Any: 解析后的响应体, 优先尝试 `JSON`, 失败回退为文本
        """
        headers = kwargs.pop("headers", None)

        logger.info("✨Request headers: {}", headers)

        ep = endpoint if endpoint.startswith("/") else "/" + endpoint
        url = f"{self.base_url}{self.base_path}{ep}"
        try:
            session = await self._get_session()
            async with session.request(method=method.upper(), url=url, headers=headers, **kwargs) as resp:

                logger.info("✨Response headers: {}", dict(resp.headers))

                status = resp.status
                text_body = await resp.text()
                try:
                    data = json.loads(text_body)
                except json.JSONDecodeError:
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
