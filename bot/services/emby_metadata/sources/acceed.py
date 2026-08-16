"""ACCEED 的站点请求适配器。"""

from urllib.parse import urlencode

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.acceed import AcceedParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class AcceedSource(HttpMetadataSource):
    """声明 ACCEED 专属的 Cookie、搜索和详情路径。"""

    name = AcceedParser.source_name
    category = AcceedParser.category
    base_url = AcceedParser.base_url
    request_timeout_seconds = 25.0
    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": f"{base_url}/",
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """按关键字搜索 ACCEED。"""
        path = "/search.php?" + urlencode({"s": keyword.strip()})
        html = await self._request_text(path)
        return AcceedParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 ACCEED 详情页。"""
        AcceedParser._validate_source_id(source_id)
        search_path = "/search.php?" + urlencode({"s": source_id})
        _, html = await self._request_text_sequence((search_path, f"/detail.{source_id}.html"))
        return AcceedParser.parse_detail(html, source_id)
