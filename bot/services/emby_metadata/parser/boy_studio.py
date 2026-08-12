import re
from collections.abc import Iterable
from datetime import date, datetime
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataPerson,
    MetadataSearchResult,
)


class BoyStudioParser:
    """解析 BOYSTUDIO 的视频搜索和详情页。"""

    source_name = "boy-studio"
    base_url = "https://boy-studio.com"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[MetadataSearchResult] = []
        seen: set[str] = set()
        for link in soup.select('a[href^="/videos/"]'):
            source_id = cls._source_id(link.get("href"))
            card = link.find_parent(class_=lambda value: value and "item" in value.split())
            if not source_id or source_id in seen or not isinstance(card, Tag):
                continue
            title_node = card.select_one(".item__title")
            title = cls._clean_text(title_node.get_text(" ", strip=True) if isinstance(title_node, Tag) else link.get_text(" ", strip=True))
            if not title:
                continue
            image = card.select_one(".item__thumbnail img")
            image_src = image.get("src", "").strip() if isinstance(image, Tag) else ""
            seen.add(source_id)
            results.append(
                MetadataSearchResult(
                    source=cls.source_name,
                    source_id=source_id,
                    category=cls.category,
                    title=title,
                    statuses=cls._labels(card),
                    image_urls=[urljoin(f"{cls.base_url}/", image_src)] if image_src else [],
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
        title_node = soup.select_one(".item__lower .item__title") or soup.select_one(".item__title")
        if not isinstance(title_node, Tag) or not title_node.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)
        original_title = cls._clean_text(title_node.get_text(" ", strip=True))
        fields = cls._fields(soup)
        product_number = fields.get("品番") or source_id
        title = f"{product_number} {original_title}"
        release_date = cls._parse_date(fields.get("配信開始日", ""))
        poster_url = cls._poster_url(soup)
        labels = cls._table_link_values(soup, "レーベル", "/videos/label/")
        tags = cls._table_link_values(soup, "ジャンル", "/videos/category/")
        series = fields.get("シリーズ")
        if series:
            tags.append(series)
        people = cls._people(soup)
        return MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            product_number=product_number,
            title=title,
            original_title=original_title,
            sort_name=title,
            forced_sort_name=title,
            overview=cls._overview(soup),
            year=release_date.year if release_date else None,
            release_date=release_date,
            genres=[],
            studios=[MetadataNamedItem(name=value) for value in labels],
            people=people,
            tags=[MetadataNamedItem(name=value) for value in cls._unique(tags)],
            external_ids={
                "source": cls.source_name,
                "source_id": source_id,
                "source_url": cls._detail_url(source_id),
                "product_number": product_number,
                "Imdb": product_number,
            },
            poster_url=poster_url,
            raw_url=cls._detail_url(source_id),
        )

    @classmethod
    def _fields(cls, soup: BeautifulSoup) -> dict[str, str]:
        fields: dict[str, str] = {}
        for row in soup.select(".table--item-data tr"):
            left = row.select_one("th")
            right = row.select_one("td")
            if isinstance(left, Tag) and isinstance(right, Tag):
                fields[cls._clean_text(left.get_text(" ", strip=True))] = cls._clean_text(right.get_text(" ", strip=True))
        return fields

    @classmethod
    def _labels(cls, container: Tag | BeautifulSoup) -> list[str]:
        return cls._unique(
            cls._clean_text(link.get_text(" ", strip=True))
            for link in container.select('a[href*="/videos/label/"]')
            if cls._clean_text(link.get_text(" ", strip=True))
        )

    @classmethod
    def _genre_values(cls, soup: BeautifulSoup) -> list[str]:
        return cls._unique(
            cls._clean_text(link.get_text(" ", strip=True))
            for link in soup.select('a[href*="/videos/category/"]')
            if cls._clean_text(link.get_text(" ", strip=True))
        )

    @classmethod
    def _table_link_values(cls, soup: BeautifulSoup, field_name: str, href_part: str) -> list[str]:
        for row in soup.select(".table--item-data tr"):
            heading = row.select_one("th")
            if not isinstance(heading, Tag) or cls._clean_text(heading.get_text(" ", strip=True)) != field_name:
                continue
            return cls._unique(
                cls._clean_text(link.get_text(" ", strip=True))
                for link in row.select(f'a[href*="{href_part}"]')
                if cls._clean_text(link.get_text(" ", strip=True))
            )
        return []

    @classmethod
    def _people(cls, soup: BeautifulSoup) -> list[MetadataPerson]:
        people: list[MetadataPerson] = []
        for link in soup.select('a[href*="/videos/model/"]'):
            name = cls._clean_text(link.get_text(" ", strip=True))
            if name:
                people.append(MetadataPerson(name=name))
        return cls._unique_people(people)

    @classmethod
    def _poster_url(cls, soup: BeautifulSoup) -> str | None:
        iframe = soup.select_one('iframe[src*="poster="]')
        if isinstance(iframe, Tag):
            poster = parse_qs(urlparse(str(iframe.get("src"))).query).get("poster", [""])[0]
            if poster:
                return unquote(poster)
        image = soup.select_one(".item__thumbnail img")
        source = image.get("src", "").strip() if isinstance(image, Tag) else ""
        return urljoin(f"{cls.base_url}/", source) if source else None

    @classmethod
    def _overview(cls, soup: BeautifulSoup) -> str | None:
        container = soup.select_one(".item__lower .item__content details div")
        if not isinstance(container, Tag):
            return None
        paragraphs = [
            cls._clean_text(paragraph.get_text(" ", strip=True))
            for paragraph in container.select("p")
            if not cls._is_commercial_notice(paragraph.get_text(" ", strip=True))
        ]
        return "\n".join(value for value in paragraphs if value) or None

    @staticmethod
    def _is_commercial_notice(value: str) -> bool:
        return "サブスク会員" in value or ("通常価格" in value and "単品" in value)

    @staticmethod
    def _parse_date(value: str) -> date | None:
        match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", value)
        return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date() if match else None

    @staticmethod
    def _source_id(href: object) -> str | None:
        if not isinstance(href, str):
            return None
        match = re.fullmatch(r"/videos/(\d+)/", href.split("?", 1)[0])
        return match.group(1) if match else None

    @staticmethod
    def _detail_url(source_id: str) -> str:
        return f"https://boy-studio.com/videos/{source_id}/"

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not source_id.isdigit():
            raise ValueError("boy-studio source_id 格式无效")

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
