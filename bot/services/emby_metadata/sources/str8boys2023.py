from urllib.parse import quote_plus
import aiohttp
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.str8boys2023 import Str8BoysParser
from bot.services.emby_metadata.sources.base import MetadataSource

class Str8BoysSource(MetadataSource):
    name=Str8BoysParser.source_name; category=Str8BoysParser.category; base_url=Str8BoysParser.base_url
    def image_headers(self, referer: str | None = None) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": referer or f"{self.base_url}/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
    async def search(self, keyword: str, limit: int = 10) -> list[MetadataSearchResult]:
        return Str8BoysParser.parse_search_results(
            await self._request(
                "/list.php?keywords="
                f"{quote_plus(keyword.strip())}&cid=1&scid=&avid=&purchased_contents="
            ),
            limit,
        )
    async def fetch_detail(self, source_id: str) -> MetadataCandidate: return Str8BoysParser.parse_detail(await self._request(Str8BoysParser.detail_url(source_id).removeprefix(self.base_url)), source_id)
    async def _request(self, path: str) -> str:
        try:
            async with aiohttp.ClientSession(headers={"User-Agent":"EmbyMetadataManager/1.0"}) as session:
                async with session.get(self.base_url + path) as response:
                    if response.status >= 400: raise MetadataSourceHTTPError(f"HTTP {response.status}", self.name)
                    return await response.text()
        except MetadataSourceHTTPError: raise
        except (aiohttp.ClientError, TimeoutError) as error: raise MetadataSourceNetworkError(str(error), self.name) from error
