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
    MetadataSearchResult,
)


_DATE_PATTERN = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class HunkChParser:
    """解析 hunk-ch 搜索结果和作品详情页面。"""

    source_name = "hunk-ch"
    base_url = "https://www.hunk-ch.com"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        """解析 hunk-ch 搜索结果页。"""
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[MetadataSearchResult] = []
        seen: set[str] = set()
        for table in soup.select("#newmovie .movie table"):
            link = table.select_one('h4 a[href*="movie_detail.php"]')
            if not isinstance(link, Tag):
                continue
            source_id = cls._source_id(link.get("href"))
            if source_id is None or source_id in seen:
                continue
            title = cls._clean_text(link.get_text(" ", strip=True))
            if not title:
                continue
            seen.add(source_id)
            results.append(
                MetadataSearchResult(
                    source=cls.source_name,
                    source_id=source_id,
                    category=cls.category,
                    title=title,
                    release_date=cls._date_from_text(table.get_text(" ", strip=True)),
                    price_yen=cls._price_from_text(table.get_text(" ", strip=True)),
                    statuses=cls._statuses(table),
                    image_urls=cls._images(table),
                    detail_url=cls._detail_url(source_id),
                )
            )
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        """解析 hunk-ch 详情页并转换为统一元数据模型。"""
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one(".product_detail_centre > h2")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)

        original_title = cls._clean_text(heading.get_text(" ", strip=True))
        data = soup.select_one("#product .data")
        data_text = data.get_text(" ", strip=True) if isinstance(data, Tag) else ""
        release_date = cls._date_from_text(data_text)
        runtime = cls._runtime_from_text(data_text)
        # hunk-ch 的分类词不是稳定的 Genre，默认不写入类型，避免误判。
        genres = cls._category_values(data)
        studio = cls._brand_value(data)
        product_number = re.sub(r"^GV-", "", source_id, flags=re.IGNORECASE)
        title = f"{product_number} {original_title}"
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
            studios=[MetadataNamedItem(name=studio)] if studio else [],
            people=[],
            tags=[MetadataNamedItem(name=value) for value in genres],
            poster_url=cls._poster_url(soup),
            external_ids={
                "source": cls.source_name,
                "source_id": source_id,
                "source_url": cls._detail_url(source_id),
                "product_number": product_number,
                "Imdb": source_id,
            },
            raw_url=cls._detail_url(source_id),
        )

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @classmethod
    def _source_id(cls, href: object) -> str | None:
        if not isinstance(href, str):
            return None
        value = parse_qs(urlparse(href).query).get("code", [None])[0]
        return value if isinstance(value, str) and _CODE_PATTERN.fullmatch(value) else None

    @classmethod
    def _detail_url(cls, source_id: str) -> str:
        return f"{cls.base_url}/movie_detail.php?code={source_id}"

    @classmethod
    def _images(cls, table: Tag) -> list[str]:
        return cls._unique(
            urljoin(f"{cls.base_url}/", str(src))
            for image in table.select("img")
            if isinstance((src := image.get("src")), str) and "pickup" in src
        )

    @classmethod
    def _poster_url(cls, soup: BeautifulSoup) -> str | None:
        image = soup.select_one(".product_detail_centre img[src*='_top.']")
        if not isinstance(image, Tag) or not isinstance(image.get("src"), str):
            return None
        return urljoin(f"{cls.base_url}/", image["src"])

    @classmethod
    def _statuses(cls, table: Tag) -> list[str]:
        values = []
        for image in table.select("img[title], img[alt]"):
            value = image.get("title") or image.get("alt")
            if isinstance(value, str) and value and value not in {"m_picture"}:
                values.append(value)
        return cls._unique(values)

    @staticmethod
    def _date_from_text(value: str) -> date | None:
        match = _DATE_PATTERN.search(value)
        return datetime.strptime(match.group(), "%Y-%m-%d").date() if match else None

    @staticmethod
    def _price_from_text(value: str) -> int | None:
        match = re.search(r"([\d,]+)円", value)
        return int(match.group(1).replace(",", "")) if match else None

    @staticmethod
    def _runtime_from_text(value: str) -> int | None:
        match = re.search(r"収録時間：\s*(\d+)分", value)
        return int(match.group(1)) if match else None

    @classmethod
    def _category_values(cls, data: Tag | None) -> list[str]:
        if not isinstance(data, Tag):
            return []
        return cls._unique(cls._clean_text(link.get_text(" ", strip=True)) for link in data.find_all("a") if link.get("href", "").startswith("search.php?c="))

    @staticmethod
    def _brand_value(data: Tag | None) -> str | None:
        if not isinstance(data, Tag):
            return None
        link = data.select_one('a[href*="search.php?b="]')
        return HunkChParser._clean_text(link.get_text(" ", strip=True)) if isinstance(link, Tag) else None

    @classmethod
    def _overview(cls, soup: BeautifulSoup) -> str | None:
        story = soup.select_one("#product .detail_title img[title='ストーリー']")
        parent = story.parent if isinstance(story, Tag) else None
        paragraph = parent.find_next("p") if isinstance(parent, Tag) else None
        return cls._clean_text(paragraph.get_text(" ", strip=True)) if isinstance(paragraph, Tag) else None

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            if isinstance(value, str) and value and value not in result:
                result.append(value)
        return result

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not _CODE_PATTERN.fullmatch(source_id):
            raise ValueError("hunk-ch source_id 格式无效")
