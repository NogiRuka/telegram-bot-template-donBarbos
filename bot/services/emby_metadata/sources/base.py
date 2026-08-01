from abc import ABC, abstractmethod

from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate


class MetadataSourceError(Exception):
    def __init__(self, message: str, source: str) -> None:
        super().__init__(f"{source}: {message}")
        self.message = message
        self.source = source


class MetadataSourceNetworkError(MetadataSourceError):
    pass


class MetadataSourceHTTPError(MetadataSourceError):
    pass


class MetadataSourceParseError(MetadataSourceError):
    pass


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
