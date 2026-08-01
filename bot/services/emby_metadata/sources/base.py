from abc import ABC, abstractmethod

from bot.services.emby_metadata.errors import (
    MetadataSourceError,
    MetadataSourceHTTPError,
    MetadataSourceNetworkError,
    MetadataSourceParseError,
)
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate


class MetadataSource(ABC):
    name: str
    category: MediaLibraryCategory
    base_url: str

    @abstractmethod
    async def search(self, keyword: str, limit: int = 10) -> list[MetadataCandidate]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        raise NotImplementedError
