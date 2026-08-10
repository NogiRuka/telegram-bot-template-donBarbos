import re
from datetime import date, datetime
from collections.abc import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataPerson,
    MetadataSearchResult,
)


class MensrushParser:
    """解析 Men's Rush 搜索页和详情页。"""

    source_name = "mensrush"
    base_url = "https://www.mensrush.tv"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        """解析 Men's Rush 搜索结果。"""
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[MetadataSearchResult] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="single.php?id="]'):
            if link.select_one("img"):
                continue
            source_id = cls._source_id(link.get("href"))
            title = re.sub(r"^(?:[MW]\s+|\[\d+\]\s*)", "", cls._clean_text(link.get_text(" ", strip=True)))
            if source_id is None or source_id in seen or not title:
                continue
            image = next(
                (
                    image_node
                    for image_node in link.find_all_previous("img", limit=20)
                    if isinstance(image_node.get("src"), str) and source_id.lower() in image_node["src"].lower()
                ),
                None,
            )
            price = link.find_previous(class_="price")
            seen.add(source_id)
            results.append(
                MetadataSearchResult(
                    source=cls.source_name,
                    source_id=source_id,
                    category=cls.category,
                    title=title,
                    price_yen=cls._price(price.get_text(" ", strip=True) if isinstance(price, Tag) else ""),
                    image_urls=[str(image["src"])] if isinstance(image, Tag) and isinstance(image.get("src"), str) else [],
                    detail_url=cls._detail_url(source_id),
                )
            )
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        """解析 Men's Rush 商品详情。"""
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one(".detail_title h2")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)
        original_title = cls._clean_text(heading.get_text(" ", strip=True))
        product_number = re.sub(r"_DL$", "", source_id, flags=re.IGNORECASE)
        movie = soup.select_one(".movie_detail")
        fields = cls._linked_fields(movie if isinstance(movie, Tag) else soup)
        overview = cls._overview(movie)
        tags = fields.get("ジャンル", [])
        return MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            product_number=product_number,
            title=f"{product_number} {original_title}",
            original_title=original_title,
            sort_name=f"{product_number} {original_title}",
            forced_sort_name=f"{product_number} {original_title}",
            overview=overview,
            year=None,
            release_date=None,
            genres=[],
            studios=[MetadataNamedItem(name=fields["メーカー"][0])] if fields.get("メーカー") else [],
            people=[MetadataPerson(name=name) for name in fields.get("モデル", [])],
            tags=[MetadataNamedItem(name=value) for value in tags],
            external_ids={
                "source": cls.source_name,
                "source_id": source_id,
                "source_url": cls._detail_url(source_id),
                "product_number": product_number,
                "Imdb": product_number,
            },
            poster_url=cls._poster_url(soup),
            raw_url=cls._detail_url(source_id),
        )

    @classmethod
    def _linked_fields(cls, container: Tag | BeautifulSoup) -> dict[str, list[str]]:
        fields: dict[str, list[str]] = {"モデル": [], "メーカー": [], "ジャンル": []}
        for link in container.select('a[href]'):
            href = str(link.get("href"))
            if "mid=" in href:
                fields["モデル"].append(cls._clean_text(link.get_text(" ", strip=True)))
            elif "maid=" in href:
                fields["メーカー"].append(cls._clean_text(link.get_text(" ", strip=True)))
            elif "geid=" in href:
                fields["ジャンル"].append(cls._clean_text(link.get_text(" ", strip=True)))
        for key in fields:
            fields[key] = cls._unique(fields[key])
        return fields

    @classmethod
    def _overview(cls, movie: Tag | None) -> str | None:
        if not isinstance(movie, Tag):
            return None
        headings = movie.find_all("h3")
        for heading in headings:
            if cls._clean_text(heading.get_text(" ", strip=True)) == "作品詳細":
                paragraph = heading.find_next_sibling("p")
                if isinstance(paragraph, Tag):
                    return cls._clean_text(paragraph.get_text(" ", strip=True)) or None
        return None

    @classmethod
    def _poster_url(cls, soup: BeautifulSoup) -> str | None:
        video = soup.select_one("video[poster]")
        source = video.get("poster") if isinstance(video, Tag) else None
        return source if isinstance(source, str) else None

    @staticmethod
    def _source_id(href: object) -> str | None:
        if not isinstance(href, str):
            return None
        value = parse_qs(urlparse(href).query).get("id", [None])[0]
        return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]+", value) else None

    @staticmethod
    def _detail_url(source_id: str) -> str:
        return f"https://www.mensrush.tv/single.php?id={source_id}"

    @staticmethod
    def _price(value: str) -> int | None:
        match = re.search(r"([\d,]+)円", value)
        return int(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", source_id):
            raise ValueError("mensrush source_id 格式无效")
