from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class MediaLibraryCategory(StrEnum):
    JAPANESE_KOREAN = "japanese_korean"
    WESTERN = "western"


class MetadataCandidate(BaseModel):
    """数据源抓取后的统一候选模型。"""

    source: str
    source_id: str
    category: MediaLibraryCategory
    title: str
    original_title: str | None = None
    overview: str | None = None
    year: int | None = None
    release_date: date | None = None
    genres: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)
    external_ids: dict[str, str] = Field(default_factory=dict)
    poster_url: str | None = None
    runtime_minutes: int | None = None
    labels: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    raw_url: str | None = None
