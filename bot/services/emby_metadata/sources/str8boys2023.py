"""str8boys2023 的站点请求适配器。"""

from urllib.parse import quote_plus

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.str8boys2023 import Str8BoysParser
from bot.services.emby_metadata.sources.base import HttpMetadataSource


class Str8BoysSource(HttpMetadataSource):
    """声明 str8boys2023 专属的搜索参数和详情路径。"""

    name = Str8BoysParser.source_name
    category = Str8BoysParser.category
    base_url = Str8BoysParser.base_url
    default_headers = {"User-Agent": "EmbyMetadataManager/1.0"}
    image_header_overrides = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36"
        )
    }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        """以 str8boys2023 官方参数搜索作品。"""
        path = (
            "/list.php?keywords="
            f"{quote_plus(keyword.strip())}&cid=1&scid=&avid=&purchased_contents="
        )
        html = await self._request_text(path)
        return Str8BoysParser.parse_search_results(html, limit)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """抓取 str8boys2023 商品详情。"""
        detail_id, product_number = Str8BoysParser._source_parts(source_id)
        if not detail_id:
            results = await self.search(product_number)
            matched_result = next(
                (
                    result
                    for result in results
                    if Str8BoysParser._source_parts(result.source_id)[1].casefold()
                    == product_number.casefold()
                ),
                None,
            )
            if matched_result is None:
                raise MetadataSourceParseError(
                    f"未找到作品番号 {product_number} 对应的详情页 ID",
                    self.name,
                )
            source_id = matched_result.source_id
        path = Str8BoysParser.detail_url(source_id).removeprefix(self.base_url)
        html = await self._request_text(path)
        return Str8BoysParser.parse_detail(html, source_id)
