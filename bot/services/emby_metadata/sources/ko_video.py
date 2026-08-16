"""ko-video 的站点请求适配器。"""

from urllib.parse import quote_plus

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_video import KoVideoParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class KoVideoSource(HttpMetadataSource):
    """声明 ko-video 专属的证书兼容、搜索和详情路径。"""

    name = KoVideoParser.source_name
    category = KoVideoParser.category
    base_url = KoVideoParser.base_url
    verify_ssl = False
    default_headers = {"User-Agent": "EmbyMetadataManager/1.0"}
    image_header_overrides = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36"
        )
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """以 ko-video 的 name 参数搜索作品。"""
        html = await self._request_text(
            f"/products/list.php?name={quote_plus(keyword.strip())}"
        )
        return KoVideoParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 ko-video 商品详情。"""
        path = KoVideoParser.detail_url(source_id).removeprefix(self.base_url)
        html = await self._request_text(path)
        return KoVideoParser.parse_detail(html, source_id)
