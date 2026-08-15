from urllib.parse import quote_plus
import aiohttp
from bot.services.emby_metadata.errors import MetadataSourceHTTPError, MetadataSourceNetworkError
from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.parser.ko_tube import KoTubeParser
from bot.services.emby_metadata.sources.base import MetadataSource

class KoTubeSource(MetadataSource):
    name=KoTubeParser.source_name; category=KoTubeParser.category; base_url=KoTubeParser.base_url
    def image_headers(self, referer: str | None = None) -> dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": referer or f"{self.base_url}/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
    async def search(self, keyword: str, limit: int=10) -> list[MetadataSearchResult]:
        if keyword.strip().upper().startswith("KT-"):
            candidate=await self.fetch_detail(keyword.strip().upper())
            return [MetadataSearchResult(source=self.name, source_id=candidate.source_id, category=self.category, title=candidate.title, release_date=candidate.release_date, price_yen=candidate.price_yen, image_urls=[candidate.poster_url] if candidate.poster_url else [], detail_url=candidate.raw_url)]
        html = await self._request_post(
            "/search/result",
            {
                "_method": "POST",
                "data[Search][keyword]": keyword.strip(),
                "data[Search][ex_keyword]": "",
                "data[Search][search_option1]": "1",
            },
        )
        return KoTubeParser.parse_search_results(html, limit)
    async def fetch_detail(self, source_id: str) -> MetadataCandidate: return KoTubeParser.parse_detail(await self._request(KoTubeParser.detail_url(source_id).removeprefix(self.base_url)), source_id)
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

    async def _request_post(self, path: str, data: dict[str, str]) -> str:
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(
                headers={"User-Agent": "EmbyMetadataManager/1.0"},
                connector=connector,
            ) as session:
                async with session.post(
                    self.base_url + path,
                    data=data,
                    allow_redirects=True,
                ) as response:
                    if response.status >= 400:
                        raise MetadataSourceHTTPError(
                            f"HTTP {response.status}", self.name
                        )
                    return await response.text()
        except MetadataSourceHTTPError:
            raise
        except (aiohttp.ClientError, TimeoutError) as error:
            raise MetadataSourceNetworkError(str(error), self.name) from error
