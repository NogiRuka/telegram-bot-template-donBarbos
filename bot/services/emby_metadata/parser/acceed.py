import re
from collections.abc import Iterable
from datetime import date, datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataPerson,
    MetadataSearchResult,
)


_DETAIL_PATH = re.compile(r"^/detail\.([A-Za-z0-9_-]+)\.html(?:[?#]|$)", re.IGNORECASE)


class AcceedParser:
    """解析 ACCEED 搜索页和作品详情页。"""

    source_name = "acceed"
    base_url = "https://acceed.jp"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[MetadataSearchResult] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/detail."]'):
            source_id = cls._source_id(link.get("href"))
            if not source_id or source_id in seen:
                continue
            card = link.find_parent(class_="item_img") or link
            title_node = card.select_one(".des h6") if isinstance(card, Tag) else None
            title_node = title_node or link
            title = cls._clean_text(title_node.get_text(" ", strip=True))
            if not title:
                continue
            image = card.select_one("img") if isinstance(card, Tag) else None
            image_src = image.get("src", "").strip() if isinstance(image, Tag) else None
            seen.add(source_id)
            results.append(
                MetadataSearchResult(
                    source=cls.source_name,
                    source_id=source_id,
                    category=cls.category,
                    title=title,
                    price_yen=cls._price(card),
                    statuses=cls._statuses(card),
                    image_urls=[urljoin(f"{cls.base_url}/", str(image_src))] if isinstance(image_src, str) else [],
                    detail_url=cls._detail_url(source_id),
                )
            )
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one(".title h2") or soup.select_one("h2")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)

        for favorite in heading.select(".favoritebtn"):
            favorite.decompose()
        original_title = cls._clean_text(heading.get_text(" ", strip=True))
        product_number = source_id.split("_", 1)[0]
        title = f"{product_number} {original_title}"
        fields = cls._detail_fields(soup)
        people = cls._people(soup)
        tags = cls._tags(soup)
        poster_urls = cls._poster_urls(soup)
        release_date = cls._parse_date(fields.get("DVD発売", ""))
        overview = cls._overview(soup)

        return MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            product_number=product_number,
            title=title,
            original_title=original_title,
            sort_name=title,
            forced_sort_name=title,
            overview=overview,
            year=release_date.year if release_date else None,
            release_date=release_date,
            genres=[],
            studios=[MetadataNamedItem(name="ACCEED")],
            people=people,
            tags=[MetadataNamedItem(name=value) for value in tags],
            external_ids={
                "source": cls.source_name,
                "source_id": source_id,
                "source_url": cls._detail_url(source_id),
                "product_number": product_number,
                "Imdb": product_number,
            },
            poster_url=poster_urls[0] if poster_urls else None,
            poster_urls=poster_urls,
            raw_url=cls._detail_url(source_id),
        )

    @classmethod
    def _people(cls, soup: BeautifulSoup) -> list[MetadataPerson]:
        people: list[MetadataPerson] = []
        for link in soup.select('a[href*="model=on"]'):
            name = cls._clean_text(str(link.get("title") or link.get_text(" ", strip=True)))
            if not name:
                continue
            image = link.select_one("img")
            image_src = image.get("src", "").strip() if isinstance(image, Tag) else None
            people.append(MetadataPerson(
                name=name,
                image_url=urljoin(f"{cls.base_url}/", str(image_src)) if isinstance(image_src, str) else None,
            ))
        return cls._unique_people(people)

    @classmethod
    def _tags(cls, soup: BeautifulSoup) -> list[str]:
        return cls._unique(
            cls._clean_text(link.get_text(" ", strip=True))
            for link in soup.select('.select a[href*="/search.php?c="]')
            if cls._clean_text(link.get_text(" ", strip=True))
        )

    @classmethod
    def _detail_fields(cls, soup: BeautifulSoup) -> dict[str, str]:
        fields: dict[str, str] = {}
        for row in soup.select(".thongso li"):
            left = row.select_one(".trai")
            right = row.select_one(".phai")
            if isinstance(left, Tag) and isinstance(right, Tag):
                fields[cls._clean_text(left.get_text(" ", strip=True))] = cls._clean_text(right.get_text(" ", strip=True))
        return fields

    @classmethod
    def _overview(cls, soup: BeautifulSoup) -> str | None:
        container = soup.select_one(".chitiet")
        if not isinstance(container, Tag):
            return None
        lines = [cls._clean_text(line) for line in container.get_text("\n", strip=True).splitlines()]
        return "\n".join(line for line in lines if line) or None

    @classmethod
    def _poster_urls(cls, soup: BeautifulSoup) -> list[str]:
        """提取详情页当前作品的原图链接，优先使用画廊链接而不是缩略图。"""
        values: list[str] = []
        for link in soup.select(".sanpham .show a[href], a.gallery1[href], a.swipebox[href]"):
            href = link.get("href")
            if isinstance(href, str) and href.strip():
                values.append(urljoin(f"{cls.base_url}/", href.strip()))
        if not values:
            image = soup.select_one(".sanpham .show img[src]")
            source = image.get("src") if isinstance(image, Tag) else None
            if isinstance(source, str) and source.strip():
                values.append(urljoin(f"{cls.base_url}/", source.strip()))
        return cls._unique(values)

    @staticmethod
    def _price(card: Tag) -> int | None:
        match = re.search(r"[￥¥]\s*([0-9,]+)", card.get_text(" ", strip=True))
        return int(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _statuses(card: Tag) -> list[str]:
        return [AcceedParser._clean_text(node.get_text(" ", strip=True)) for node in card.select(".center-align") if AcceedParser._clean_text(node.get_text(" ", strip=True))]

    @staticmethod
    def _parse_date(value: str) -> date | None:
        match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", value)
        return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date() if match else None

    @staticmethod
    def _source_id(href: object) -> str | None:
        if not isinstance(href, str):
            return None
        match = _DETAIL_PATH.match(href)
        return match.group(1) if match else None

    @staticmethod
    def _detail_url(source_id: str) -> str:
        return f"https://acceed.jp/detail.{source_id}.html"

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", source_id):
            raise ValueError("acceed source_id 格式无效")

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _unique_people(values: Iterable[MetadataPerson]) -> list[MetadataPerson]:
        result: list[MetadataPerson] = []
        seen: set[str] = set()
        for person in values:
            key = person.name.strip().casefold()
            if key and key not in seen:
                result.append(person)
                seen.add(key)
        return result
