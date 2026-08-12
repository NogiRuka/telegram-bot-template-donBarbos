from urllib.parse import urlencode

import aiohttp

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.boy_studio import BoyStudioParser
from bot.services.emby_metadata.sources.base import MetadataSource


class BoyStudioSource(MetadataSource):
    name = BoyStudioParser.source_name
    category = BoyStudioParser.category
    base_url = BoyStudioParser.base_url

    def __init__(self, timeout_seconds: float = 25.0, cookie_manager: CookieManager | None = None) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": f"{self.base_url}/",
        }
        cookie = (cookie_manager or CookieManager()).get_cookie(self.name)
        if cookie:
            self._headers["Cookie"] = cookie

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        html = await self._request("/videos/?" + urlencode({"q": keyword.strip()}))
        return BoyStudioParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        BoyStudioParser._validate_source_id(source_id)
        return BoyStudioParser.parse_detail(await self._request(f"/videos/{source_id}/"), source_id)

    async def _request(self, path: str) -> str:
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with aiohttp.ClientSession(timeout=self._timeout, headers=self._headers) as session:
                    async with session.get(f"{self.base_url}{path}") as response:
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
