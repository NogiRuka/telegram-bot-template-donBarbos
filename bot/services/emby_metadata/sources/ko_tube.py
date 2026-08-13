from urllib.parse import quote_plus
import aiohttp
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_tube import KoTubeParser
from bot.services.emby_metadata.sources.base import MetadataSource

class KoTubeSource(MetadataSource):
    name=KoTubeParser.source_name; category=KoTubeParser.category; base_url=KoTubeParser.base_url
    async def search(self, keyword: str, limit: int=10) -> list[MetadataSearchResult]:
        if keyword.strip().upper().startswith("KT-"):
            candidate=await self.fetch_detail(keyword.strip().upper())
            return [MetadataSearchResult(source=self.name, source_id=candidate.source_id, category=self.category, title=candidate.title, release_date=candidate.release_date, detail_url=candidate.raw_url)]
        return KoTubeParser.parse_search_results(await self._request(f"/search?keyword={quote_plus(keyword.strip())}"), limit)
    async def fetch_detail(self, source_id: str) -> MetadataCandidate: return KoTubeParser.parse_detail(await self._request(KoTubeParser.detail_url(source_id).removeprefix(self.base_url)), source_id)
    async def _request(self, path: str) -> str:
        try:
            async with aiohttp.ClientSession(headers={"User-Agent":"EmbyMetadataManager/1.0"}) as session:
                async with session.get(self.base_url + path) as response:
                    if response.status >= 400: raise MetadataSourceHTTPError(f"HTTP {response.status}", self.name)
                    return await response.text()
        except MetadataSourceHTTPError: raise
        except (aiohttp.ClientError, TimeoutError) as error: raise MetadataSourceNetworkError(str(error), self.name) from error
