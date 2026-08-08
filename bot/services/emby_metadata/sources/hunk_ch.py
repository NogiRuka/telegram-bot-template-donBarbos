from urllib.parse import urlencode

import aiohttp

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.hunk_ch import HunkChParser


class HunkChSource:
    """hunk-ch 数据源的 HTTP 请求和解析编排。"""

    name = HunkChParser.source_name
    category = HunkChParser.category
    base_url = HunkChParser.base_url

    def __init__(self, timeout_seconds: float = 25.0, cookie_manager: CookieManager | None = None) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {
            "User-Agent": "EmbyMetadataManager/1.0 (+private metadata lookup)",
            "Accept-Language": "ja,en;q=0.8",
        }
        cookie = (cookie_manager or CookieManager()).get_cookie(self.name)
        if cookie:
            self._headers["Cookie"] = cookie

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 hunk-ch 作品。"""
        html = await self._request("/search.php?" + urlencode({"s": keyword.strip(), "search_flag": "all"}))
        results = HunkChParser.parse_search_results(html, limit)
        normalized_keyword = "".join(character for character in keyword.upper() if character.isalnum())
        if normalized_keyword and any(character.isdigit() for character in normalized_keyword):
            results = [
                result
                for result in results
                if normalized_keyword in "".join(character for character in result.source_id.upper() if character.isalnum())
                or normalized_keyword in "".join(character for character in result.title.upper() if character.isalnum())
            ]
        return results[:limit]

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取并解析 hunk-ch 详情。"""
        HunkChParser._validate_source_id(source_id)
        html = await self._request("/movie_detail.php?" + urlencode({"code": source_id}))
        return HunkChParser.parse_detail(html, source_id)

    def image_headers(self, referer: str | None = None) -> dict[str, str]:
        """返回 hunk-ch 图片代理请求头。"""
        return {**self._headers, "Referer": referer or f"{self.base_url}/"}

    async def _request(self, path: str) -> str:
        url = f"{self.base_url}{path}"
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

    parse_search_results = HunkChParser.parse_search_results
    parse_detail = HunkChParser.parse_detail
