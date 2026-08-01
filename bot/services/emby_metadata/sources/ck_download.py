from urllib.parse import urljoin

import aiohttp

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.matching import calculate_confidence
from bot.services.emby_metadata.models import MetadataCandidate
from bot.services.emby_metadata.parser.ck_download import CkDownloadParser
from bot.services.emby_metadata.sources.base import (
    MetadataSource,
    MetadataSourceHTTPError,
    MetadataSourceNetworkError,
)


class CkDownloadSource(MetadataSource):
    """ck-download 数据源：负责请求、Cookie 和搜索流程编排。"""

    name = CkDownloadParser.source_name
    category = CkDownloadParser.category
    base_url = CkDownloadParser.base_url

    def __init__(self, timeout_seconds: float = 15.0, cookie_manager: CookieManager | None = None) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {
            "User-Agent": "EmbyMetadataManager/1.0 (+private metadata lookup)",
            "Accept-Language": "ja,en;q=0.8",
        }
        cookie = (cookie_manager or CookieManager()).get_cookie(self.name)
        if cookie:
            self._headers["Cookie"] = cookie

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataCandidate]:
        """提交关键词搜索，并获取候选详情。"""
        search_keyword = keyword.strip()
        if limit <= 0 or not search_keyword:
            return []

        html = await self._request(
            "/product/search",
            method="POST",
            data={"kw": search_keyword, "kw_opt": "1", "only_nm": "0"},
        )
        summaries = CkDownloadParser.parse_search_results(html, limit)
        candidates: list[MetadataCandidate] = []
        for source_id, summary_title in summaries:
            candidate = await self.fetch_detail(source_id)
            candidate.confidence = calculate_confidence(
                search_keyword,
                candidate.title or summary_title,
                candidate.product_number,
            )
            candidates.append(candidate)
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """请求指定商品详情，并交给纯解析器处理。"""
        CkDownloadParser._validate_source_id(source_id)
        html = await self._request(f"/product/detail/{source_id}")
        return CkDownloadParser.parse_detail(html, source_id)

    async def _request(
        self,
        path: str,
        method: str = "GET",
        data: dict[str, str] | None = None,
    ) -> str:
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        try:
            async with aiohttp.ClientSession(timeout=self._timeout, headers=self._headers) as session:
                async with session.request(method, url, data=data) as response:
                    if response.status >= 400:
                        message = f"HTTP {response.status}: {response.reason}"
                        raise MetadataSourceHTTPError(message, self.name)
                    return await response.text()
        except MetadataSourceHTTPError:
            raise
        except (aiohttp.ClientError, TimeoutError) as error:
            raise MetadataSourceNetworkError(str(error), self.name) from error

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[tuple[str, str]]:
        """兼容入口：委托给 ck-download 纯解析器。"""
        return CkDownloadParser.parse_search_results(html, limit)

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        """兼容入口：委托给 ck-download 纯解析器。"""
        return CkDownloadParser.parse_detail(html, source_id)
