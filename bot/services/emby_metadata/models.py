from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class MediaLibraryCategory(str, Enum):
    """媒体库分类，用于限制数据源的适用范围。"""

    DOMESTIC = "domestic"
    JAPANESE_KOREAN = "japanese_korean"
    WESTERN = "western"


class MetadataPerson(BaseModel):
    """可写入 Emby People 字段的演职员信息。"""

    name: str = Field(description="演员或演职员姓名")
    role: str | None = Field(default=None, description="角色名，数据源未提供时留空")
    type: str = Field(default="Actor", description="Emby 人员类型，出演模型统一为 Actor")


class MetadataCandidate(BaseModel):
    """数据源详情页解析后的统一元数据候选。"""

    source: str = Field(description="数据源唯一名称")
    source_id: str = Field(description="数据源站内商品 ID")
    category: MediaLibraryCategory = Field(description="候选所属媒体库分类")
    product_number: str | None = Field(default=None, description="商品番号")
    title: str = Field(description="Emby 显示标题，格式为“番号 商品标题”")
    original_title: str = Field(description="数据源商品标题，不包含番号前缀")
    sort_name: str = Field(description="Emby 排序名，与显示标题保持一致")
    forced_sort_name: str = Field(description="Emby 强制排序名，与显示标题保持一致")
    overview: str | None = Field(default=None, description="商品简介，仅取详情页 intro_text 区域")
    year: int | None = Field(default=None, description="制作年份，优先取发布日期年份")
    release_date: date | None = Field(default=None, description="商品发布日期")
    genres: list[str] = Field(default_factory=list, description="播放内容分类，可写入 Emby Genres")
    studios: list[str] = Field(default_factory=list, description="厂家或工作室名称")
    people: list[MetadataPerson] = Field(default_factory=list, description="出演模型列表")
    labels: list[str] = Field(default_factory=list, description="标签、模型类型及 DVD 信息的去重集合")
    external_ids: dict[str, str] = Field(default_factory=dict, description="外部 ID，默认不填")
    poster_url: str | None = Field(default=None, description="商品主图 URL，固定选择编号为 1 的图片")
    runtime_minutes: int | None = Field(default=None, description="片长分钟数，秒数达到 30 时进位")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="搜索候选匹配置信度")
    raw_url: str = Field(description="数据源详情页 URL")
