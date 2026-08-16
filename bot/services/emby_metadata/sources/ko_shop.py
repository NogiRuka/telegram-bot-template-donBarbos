"""Ko-Shop 的站点请求适配器。"""

from urllib.parse import urlencode

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_shop import KoShopParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class KoShopSource(HttpMetadataSource):
    """声明 Ko-Shop 专属的 Cookie、证书兼容和页面路径。"""

    name = KoShopParser.source_name
    category = KoShopParser.category
    base_url = KoShopParser.base_url
    verify_ssl = False
    request_timeout_seconds = 25.0
    default_headers = {
        "User-Agent": "EmbyMetadataManager/1.0",
        "Accept-Language": "ja,en;q=0.8",
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 Ko-Shop 商品。"""
        path = "/products/list.php?" + urlencode({"word": keyword.strip()})
        html = await self._request_text(path)
        return KoShopParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 Ko-Shop 商品详情。"""
        KoShopParser._validate_source_id(source_id)
        html = await self._request_text(f"/products/detail.php?product_id={source_id}")
        return KoShopParser.parse_detail(html, source_id)
