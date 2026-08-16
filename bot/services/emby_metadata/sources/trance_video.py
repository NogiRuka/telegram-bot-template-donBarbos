"""trance-video 的站点请求适配器。"""

from urllib.parse import quote_plus

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.trance_video import TranceVideoParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class TranceVideoSource(HttpMetadataSource):
    """声明 trance-video 的 302 搜索流程和详情路径。"""

    name = TranceVideoParser.source_name
    category = TranceVideoParser.category
    base_url = TranceVideoParser.base_url
    default_headers = {"User-Agent": "EmbyMetadataManager/1.0"}
    image_header_overrides = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36"
        )
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """先请求搜索入口并在同一请求中跟随 302 到结果页。"""
        path = f"/product/search?keyword={quote_plus(keyword.strip())}"
        html = await self._request_text(path, allow_redirects=True)
        return TranceVideoParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 trance-video 商品详情。"""
        path = TranceVideoParser.detail_url(source_id).removeprefix(self.base_url)
        html = await self._request_text(path)
        return TranceVideoParser.parse_detail(html, source_id)
