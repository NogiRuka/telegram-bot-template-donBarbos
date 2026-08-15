"""ck-download 的站点请求适配器。"""

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ck_download import CkDownloadParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class CkDownloadSource(HttpMetadataSource):
    """声明 ck-download 专属的 Cookie、请求头、搜索表单和详情路径。"""

    name = CkDownloadParser.source_name
    category = CkDownloadParser.category
    base_url = CkDownloadParser.base_url
    cookie_key = name
    default_headers = {
        "User-Agent": "EmbyMetadataManager/1.0 (+private metadata lookup)",
        "Accept-Language": "ja,en;q=0.8",
    }

    async def search(
        self,
        keyword: str,
        limit: int = 10,
    ) -> list[MetadataSearchResult]:
        """以 ck-download 规定的 POST 表单搜索作品。"""
        search_keyword = keyword.strip()
        if limit <= 0 or not search_keyword:
            return []

        html = await self._request_text(
            "/product/search",
            method="POST",
            form_data={
                "kw": search_keyword,
                "kw_opt": "1",
                "only_nm": "0",
            },
        )
        return CkDownloadParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """请求详情页，并交由 ck-download parser 解析。"""
        CkDownloadParser._validate_source_id(source_id)
        html = await self._request_text(f"/product/detail/{source_id}")
        return CkDownloadParser.parse_detail(html, source_id)
