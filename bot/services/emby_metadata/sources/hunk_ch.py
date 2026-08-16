"""Hunk-Ch 的站点请求适配器。"""

from urllib.parse import urlencode

from bot.services.emby_metadata.matching import normalize_search_keyword
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.hunk_ch import HunkChParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class HunkChSource(HttpMetadataSource):
    """声明 Hunk-Ch 专属的 Cookie、搜索和详情路径。"""

    name = HunkChParser.source_name
    category = HunkChParser.category
    base_url = HunkChParser.base_url
    request_timeout_seconds = 25.0
    default_headers = {
        "User-Agent": "EmbyMetadataManager/1.0 (+private metadata lookup)",
        "Accept-Language": "ja,en;q=0.8",
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 Hunk-Ch，并保留番号的严格筛选。"""
        normalized_keyword = normalize_search_keyword(keyword)
        path = "/search.php?" + urlencode(
            {"s": normalized_keyword, "search_flag": "all"}
        )
        html = await self._request_text(path)
        results = HunkChParser.parse_search_results(html, limit)
        comparison_key = "".join(
            character for character in normalized_keyword.upper() if character.isalnum()
        )
        if comparison_key and any(character.isdigit() for character in comparison_key):
            results = [
                result
                for result in results
                if comparison_key
                in "".join(
                    character for character in result.source_id.upper() if character.isalnum()
                )
                or comparison_key
                in "".join(
                    character for character in result.title.upper() if character.isalnum()
                )
            ]
        return results[:limit]

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 Hunk-Ch 详情页。"""
        HunkChParser._validate_source_id(source_id)
        path = "/movie_detail.php?" + urlencode({"code": source_id})
        html = await self._request_text(path)
        return HunkChParser.parse_detail(html, source_id)
