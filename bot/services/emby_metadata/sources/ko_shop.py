from urllib.parse import urlencode

import aiohttp

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_shop import KoShopParser
from bot.services.emby_metadata.sources.base import MetadataSource


class KoShopSource(MetadataSource):
    """ko-shop 的请求和解析入口。"""

    name = KoShopParser.source_name
    category = KoShopParser.category
    base_url = KoShopParser.base_url

    def __init__(self, timeout_seconds: float = 25.0, cookie_manager: CookieManager | None = None) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {"User-Agent": "EmbyMetadataManager/1.0", "Accept-Language": "ja,en;q=0.8"}
        cookie = (cookie_manager or CookieManager()).get_cookie(self.name)
        if cookie:
            self._headers["Cookie"] = cookie

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 ko-shop 商品。"""
        html = await self._request("/products/list.php?" + urlencode({"word": keyword.strip()}))
        return KoShopParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 ko-shop 商品详情。"""
        KoShopParser._validate_source_id(source_id)
        html = await self._request(f"/products/detail.php?product_id={source_id}")
        return KoShopParser.parse_detail(html, source_id)

    async def _request(self, path: str) -> str:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(
                    timeout=self._timeout,
                    headers=self._headers,
                    connector=connector,
                ) as session:
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
