"""ck-download 的网络请求适配器。"""

from urllib.parse import urljoin

import aiohttp

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.errors import (
    MetadataSourceHTTPError,
    MetadataSourceNetworkError,
)
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ck_download import CkDownloadParser
from bot.services.emby_metadata.sources.base import MetadataSource


class CkDownloadSource(MetadataSource):
    """负责 ck-download 的 HTTP 请求、Cookie 和搜索流程。"""

    name = CkDownloadParser.source_name
    category = CkDownloadParser.category
    base_url = CkDownloadParser.base_url
    _MAX_REQUEST_ATTEMPTS = 2

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        cookie_manager: CookieManager | None = None,
    ) -> None:
        """初始化请求超时和本站 Cookie。

        Cookie 仅保存在本 source 的请求头中，并同时用于详情、搜索和图片请求。
        """
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {
            "User-Agent": "EmbyMetadataManager/1.0 (+private metadata lookup)",
            "Accept-Language": "ja,en;q=0.8",
        }
        cookie = (cookie_manager or CookieManager()).get_cookie(self.name)
        if cookie:
            self._headers["Cookie"] = cookie

    async def search(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[MetadataSearchResult]:
        """以本站规定的 POST 表单搜索作品。"""
        search_keyword = keyword.strip()
        if limit <= 0 or not search_keyword:
            return []

        html = await self._request_text(
            "/product/search",
            method="POST",
            form_data={
                "kw": search_keyword,
                "kw_opt": "1",
                "only_nm": "0",
            },
        )
        return CkDownloadParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """请求详情页，并交由纯 HTML parser 解析。"""
        CkDownloadParser._validate_source_id(source_id)
        html = await self._request_text(f"/product/detail/{source_id}")
        return CkDownloadParser.parse_detail(html, source_id)

    def image_headers(self, referer: str | None = None) -> dict[str, str]:
        """返回下载本站图片时所需的 Referer 和 Cookie 请求头。"""
        return {
            **self._headers,
            "Referer": referer or f"{self.base_url}/",
            "Accept": (
                "image/avif,image/webp,image/apng,image/svg+xml,image/*,"
                "*/*;q=0.8"
            ),
        }

    async def _request_text(
        self,
        path: str,
        *,
        method: str = "GET",
        form_data: dict[str, str] | None = None,
    ) -> str:
        """按指定方法请求本站页面，并将异常统一转换为领域错误。"""
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        last_network_error: Exception | None = None

        for attempt in range(self._MAX_REQUEST_ATTEMPTS):
            try:
                async with aiohttp.ClientSession(
                    timeout=self._timeout,
                    headers=self._headers,
                ) as session:
                    async with session.request(
                        method,
                        url,
                        data=form_data,
                    ) as response:
                        if response.status >= 400:
                            message = f"HTTP {response.status}: {response.reason}"
                            raise MetadataSourceHTTPError(message, self.name)
                        return await response.text()
            except MetadataSourceHTTPError:
                raise
            except (aiohttp.ClientError, TimeoutError) as error:
                last_network_error = error
                if attempt + 1 == self._MAX_REQUEST_ATTEMPTS:
                    break

        raise MetadataSourceNetworkError(
            str(last_network_error or "请求失败"),
            self.name,
        )
