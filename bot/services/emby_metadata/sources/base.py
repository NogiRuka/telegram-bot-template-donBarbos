"""元数据数据源的抽象接口和通用 HTTP 能力。"""

from abc import ABC, abstractmethod
from urllib.parse import urljoin

import aiohttp

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.errors import (
    MetadataSourceError,
    MetadataSourceHTTPError,
    MetadataSourceNetworkError,
    MetadataSourceParseError,
)
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataSearchResult,
)


class MetadataSource(ABC):
    """所有元数据数据源必须实现的业务接口。"""

    name: str
    category: MediaLibraryCategory
    base_url: str

    @abstractmethod
    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索来源网站并返回轻量候选结果。"""
        raise NotImplementedError

    @abstractmethod
    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取并解析指定来源 ID 的详情页。"""
        raise NotImplementedError


class HttpMetadataSource(MetadataSource):
    """提供可复用的 HTTP、Cookie、重试和图片请求能力。

    子类只声明本站的请求头、Cookie 标识、证书策略和 URL/表单差异；公共层
    不得根据 source 名称判断网站行为。
    """

    default_headers: dict[str, str] = {}
    cookie_key: str | None = None
    verify_ssl = True
    max_request_attempts = 2

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        cookie_manager: CookieManager | None = None,
    ) -> None:
        """初始化超时配置和 Cookie 提供者。"""
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._cookie_manager = cookie_manager or CookieManager()

    def image_headers(self, referer: str | None = None) -> dict[str, str]:
        """返回下载来源图片时使用的请求头。"""
        return {
            **self._request_headers(),
            "Referer": referer or f"{self.base_url}/",
            "Accept": (
                "image/avif,image/webp,image/apng,image/svg+xml,image/*,"
                "*/*;q=0.8"
            ),
        }

    def _request_headers(self) -> dict[str, str]:
        """构建本站 HTML 和图片请求共用的基础请求头。"""
        headers = dict(self.default_headers)
        if self.cookie_key:
            cookie = self._cookie_manager.get_cookie(self.cookie_key)
            if cookie:
                headers["Cookie"] = cookie
        return headers

    async def _request_text(
        self,
        path: str,
        *,
        method: str = "GET",
        form_data: dict[str, str] | None = None,
        allow_redirects: bool = True,
    ) -> str:
        """请求文本页面，并转换 HTTP 与网络异常。"""
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        last_network_error: Exception | None = None

        for attempt in range(self.max_request_attempts):
            try:
                connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
                async with aiohttp.ClientSession(
                    timeout=self._timeout,
                    headers=self._request_headers(),
                    connector=connector,
                ) as session:
                    async with session.request(
                        method,
                        url,
                        data=form_data,
                        allow_redirects=allow_redirects,
                    ) as response:
                        if response.status >= 400:
                            message = f"HTTP {response.status}: {response.reason}"
                            raise MetadataSourceHTTPError(message, self.name)
                        return await response.text()
            except MetadataSourceHTTPError:
                raise
            except (aiohttp.ClientError, TimeoutError) as error:
                last_network_error = error
                if attempt + 1 == self.max_request_attempts:
                    break

        raise MetadataSourceNetworkError(
            str(last_network_error or "请求失败"),
            self.name,
        )
