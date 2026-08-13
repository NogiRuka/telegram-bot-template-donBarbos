from urllib.parse import quote_plus
import aiohttp
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_video import KoVideoParser
from bot.services.emby_metadata.sources.base import MetadataSource

class KoVideoSource(MetadataSource):
    name=KoVideoParser.source_name; category=KoVideoParser.category; base_url=KoVideoParser.base_url
    async def search(self, keyword: str, limit: int=10) -> list[MetadataSearchResult]: return KoVideoParser.parse_search_results(await self._request(f"/products/list.php?keyword={quote_plus(keyword.strip())}"), limit)
    async def fetch_detail(self, source_id: str) -> MetadataCandidate: return KoVideoParser.parse_detail(await self._request(KoVideoParser.detail_url(source_id).removeprefix(self.base_url)), source_id)
    async def _request(self, path: str) -> str:
        try:
            async with aiohttp.ClientSession(headers={"User-Agent":"EmbyMetadataManager/1.0"}) as session:
                async with session.get(self.base_url + path) as response:
                    if response.status >= 400: raise MetadataSourceHTTPError(f"HTTP {response.status}", self.name)
                    return await response.text()
        except MetadataSourceHTTPError: raise
        except (aiohttp.ClientError, TimeoutError) as error: raise MetadataSourceNetworkError(str(error), self.name) from error
