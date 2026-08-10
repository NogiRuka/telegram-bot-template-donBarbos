from urllib.parse import urlencode

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.jgvdata import JgvdataParser
from bot.services.emby_metadata.sources.base import MetadataSource

import aiohttp


class JgvdataSource(MetadataSource):
    """jgvdata 的请求和解析入口。"""

    name = JgvdataParser.source_name
    category = JgvdataParser.category
    base_url = JgvdataParser.base_url

    def __init__(self, timeout_seconds: float = 25.0, cookie_manager: CookieManager | None = None) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {"User-Agent": "EmbyMetadataManager/1.0", "Accept-Language": "ja,en;q=0.8"}
        cookie = (cookie_manager or CookieManager()).get_cookie(self.name)
        if cookie:
            self._headers["Cookie"] = cookie

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 jgvdata 文章。"""
        html = await self._request("/?" + urlencode({"s": keyword.strip()}))
        return JgvdataParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """按编号定位并抓取 jgvdata 文章详情。"""
        search_html = await self._request("/?" + urlencode({"s": source_id}))
        results = JgvdataParser.parse_search_results(search_html, limit=50)
        result = next((item for item in results if item.source_id == source_id), None)
        if result is None:
            raise ValueError(f"jgvdata 未找到作品: {source_id}")
        html = await self._request(result.detail_url)
        return JgvdataParser.parse_detail(html, source_id)

    async def _request(self, url_or_path: str) -> str:
        url = url_or_path if url_or_path.startswith("http") else f"{self.base_url}{url_or_path}"
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession(timeout=self._timeout, headers=self._headers) as session:
                    async with session.get(url) as response:
                        if response.status >= 400:
                            raise MetadataSourceHTTPError(f"HTTP {response.status}: {response.reason}", self.name)
                        return await response.text()
            except MetadataSourceHTTPError:
                raise
            except (aiohttp.ClientError, TimeoutError) as error:
                last_error = error
                if attempt == 0:
                    continue
        raise MetadataSourceNetworkError(str(last_error or "请求失败"), self.name)
