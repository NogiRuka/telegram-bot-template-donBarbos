from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class MediaLibraryCategory(str, Enum):
    """媒体库分类，用于限制数据源的适用范围。"""

    DOMESTIC = "domestic"
    JAPANESE_KOREAN = "japanese_korean"
    WESTERN = "western"


class MetadataNamedItem(BaseModel):
    """可写入 Emby 命名对象字段的统一模型。"""

    name: str = Field(description="对象显示名称")
    id: str | None = Field(default=None, description="Emby 内部关联 ID，未知时留空")


class MetadataPerson(BaseModel):
    """可写入 Emby People 字段的演职员信息。"""

    name: str = Field(description="演员或演职员姓名")
    role: str | None = Field(default=None, description="角色名，数据源未提供时留空")
    type: str = Field(default="Actor", description="Emby 人员类型，出演模型统一为 Actor")
    image_url: str | None = Field(default=None, description="角色主图来源地址，数据源未提供时留空")
    image_data: str | None = Field(default=None, description="自定义角色主图 Base64，优先于 image_url")
    image_path: str | None = Field(default=None, description="自定义角色主图本地路径，优先于 image_url")


class MetadataSearchResult(BaseModel):
    """搜索结果页的轻量信息，供用户选择详情抓取目标。"""

    source: str = Field(description="数据源唯一名称")
    source_id: str = Field(description="数据源站内商品 ID")
    category: MediaLibraryCategory = Field(description="候选所属媒体库分类")
    title: str = Field(description="搜索结果标题")
    release_date: date | None = Field(default=None, description="搜索结果页显示的发布日期")
    price_yen: int | None = Field(default=None, description="搜索结果页显示的日元价格")
    statuses: list[str] = Field(default_factory=list, description="商品状态，例如单品、HD、租赁")
    image_urls: list[str] = Field(default_factory=list, description="搜索结果页轮播图片 URL")
    detail_url: str = Field(description="商品详情页 URL")


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
    genres: list[MetadataNamedItem] = Field(default_factory=list, description="播放内容分类，对应 Emby Genres/GenreItems")
    studios: list[MetadataNamedItem] = Field(default_factory=list, description="厂家或工作室名称，对应 Emby Studios")
    people: list[MetadataPerson] = Field(default_factory=list, description="出演模型列表")
    tags: list[MetadataNamedItem] = Field(default_factory=list, description="标签及其它辅助信息的集合，对应 Emby TagItems")
    taglines: str | None = Field(default=None, description="宣传语 / 副标题 / 一句话简介，对应 Emby Taglines")
    external_ids: dict[str, str] = Field(
        default_factory=dict,
        description="对应 Emby ProviderIds，固定使用 source/source_id/source_url/product_number 结构",
    )
    poster_url: str | None = Field(default=None, description="商品主图 URL，固定选择编号为 1 的图片")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="搜索候选匹配置信度")
    raw_url: str = Field(description="数据源详情页 URL")
