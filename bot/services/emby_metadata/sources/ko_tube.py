"""ko-tube 的站点请求适配器。"""

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_tube import KoTubeParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class KoTubeSource(HttpMetadataSource):
    """声明 ko-tube 专属的证书兼容、POST 搜索和 KT package 规则。"""

    name = KoTubeParser.source_name
    category = KoTubeParser.category
    base_url = KoTubeParser.base_url
    verify_ssl = False
    default_headers = {"User-Agent": "EmbyMetadataManager/1.0"}
    image_header_overrides = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36"
        )
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """搜索 ko-tube；KT 番号直接定位 package。"""
        normalized_keyword = keyword.strip()
        if normalized_keyword.upper().startswith("KT-"):
            candidate = await self.fetch_detail(normalized_keyword.upper())
            return [
                MetadataSearchResult(
                    source=self.name,
                    source_id=candidate.source_id,
                    category=self.category,
                    title=candidate.title,
                    release_date=candidate.release_date,
                    price_yen=candidate.price_yen,
                    image_urls=[candidate.poster_url] if candidate.poster_url else [],
                    detail_url=candidate.raw_url,
                )
            ]

        html = await self._request_text(
            "/search/result",
            method="POST",
            form_data={
                "_method": "POST",
                "data[Search][keyword]": normalized_keyword,
                "data[Search][ex_keyword]": "",
                "data[Search][search_option1]": "1",
            },
        )
        return KoTubeParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 ko-tube product 或 package 详情。"""
        path = KoTubeParser.detail_url(source_id).removeprefix(self.base_url)
        html = await self._request_text(path)
        return KoTubeParser.parse_detail(html, source_id)
