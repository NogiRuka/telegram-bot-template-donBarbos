from urllib.parse import quote_plus
import aiohttp
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_video import KoVideoParser
from bot.services.emby_metadata.sources.base import MetadataSource

class KoVideoSource(MetadataSource):
    name=KoVideoParser.source_name; category=KoVideoParser.category; base_url=KoVideoParser.base_url
    def image_headers(self, referer: str | None = None) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": referer or f"{self.base_url}/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
    async def search(self, keyword: str, limit: int=10) -> list[MetadataSearchResult]: return KoVideoParser.parse_search_results(await self._request(f"/products/list.php?name={quote_plus(keyword.strip())}"), limit)
    async def fetch_detail(self, source_id: str) -> MetadataCandidate: return KoVideoParser.parse_detail(await self._request(KoVideoParser.detail_url(source_id).removeprefix(self.base_url)), source_id)
    async def _request(self, path: str) -> str:
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(
                headers={"User-Agent": "EmbyMetadataManager/1.0"},
                connector=connector,
            ) as session:
                async with session.get(self.base_url + path) as response:
                    if response.status >= 400: raise MetadataSourceHTTPError(f"HTTP {response.status}", self.name)
                    return await response.text()
        except MetadataSourceHTTPError: raise
        except (aiohttp.ClientError, TimeoutError) as error: raise MetadataSourceNetworkError(str(error), self.name) from error
