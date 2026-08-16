"""Boy Studio 的站点请求适配器。"""

from urllib.parse import urlencode

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.boy_studio import BoyStudioParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class BoyStudioSource(HttpMetadataSource):
    """声明 Boy Studio 所需的浏览器请求头、Cookie 和页面路径。"""

    name = BoyStudioParser.source_name
    category = BoyStudioParser.category
    base_url = BoyStudioParser.base_url
    request_timeout_seconds = 25.0
    default_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": f"{base_url}/",
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """按作品标题搜索 Boy Studio。"""
        path = "/videos/?" + urlencode({"q": keyword.strip()})
        html = await self._request_text(path)
        return BoyStudioParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 Boy Studio 视频详情。"""
        BoyStudioParser._validate_source_id(source_id)
        html = await self._request_text(f"/videos/{source_id}/")
        return BoyStudioParser.parse_detail(html, source_id)
