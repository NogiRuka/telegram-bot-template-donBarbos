"""JGVData 的站点请求适配器。"""

from urllib.parse import urlencode

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.jgvdata import JgvdataParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class JgvdataSource(HttpMetadataSource):
    """声明 JGVData 专属的 Cookie、搜索和详情定位流程。"""

    name = JgvdataParser.source_name
    category = JgvdataParser.category
    base_url = JgvdataParser.base_url
    request_timeout_seconds = 25.0
    default_headers = {
        "User-Agent": "EmbyMetadataManager/1.0",
        "Accept-Language": "ja,en;q=0.8",
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 JGVData 文章。"""
        html = await self._request_text("/?" + urlencode({"s": keyword.strip()}))
        return JgvdataParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """先搜索定位 JGVData 详情链接，再抓取详情页。"""
        search_html = await self._request_text("/?" + urlencode({"s": source_id}))
        results = JgvdataParser.parse_search_results(search_html, limit=50)
        result = next((item for item in results if item.source_id == source_id), None)
        if result is None:
            raise ValueError(f"jgvdata 未找到作品: {source_id}")
        html = await self._request_text(result.detail_url)
        return JgvdataParser.parse_detail(html, source_id)
