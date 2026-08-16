"""Men's Rush 的站点请求适配器。"""

from urllib.parse import urlencode

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.mensrush import MensrushParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class MensrushSource(HttpMetadataSource):
    """声明 Men's Rush 专属的 Cookie、搜索和详情路径。"""

    name = MensrushParser.source_name
    category = MensrushParser.category
    base_url = MensrushParser.base_url
    request_timeout_seconds = 25.0
    default_headers = {
        "User-Agent": "EmbyMetadataManager/1.0",
        "Accept-Language": "ja,en;q=0.8",
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 Men's Rush，并筛选与输入匹配的正式结果。"""
        html = await self._request_text(
            "/list.php?" + urlencode({"keyword": keyword.strip()})
        )
        results = MensrushParser.parse_search_results(html, limit=100)
        normalized_keyword = keyword.strip().upper()
        if normalized_keyword:
            results = [
                result
                for result in results
                if normalized_keyword in result.source_id.upper()
                or normalized_keyword in result.title.upper()
            ]
        return results[:limit]

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 Men's Rush 商品详情。"""
        MensrushParser._validate_source_id(source_id)
        html = await self._request_text(
            "/single.php?" + urlencode({"id": source_id})
        )
        return MensrushParser.parse_detail(html, source_id)
