import re
from datetime import date, datetime
from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataSearchResult,
)


_DATE_PATTERN = re.compile(r"([A-Z][a-z]{2})\.?\s+(\d{1,2}),\s+(\d{4})")
_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class JgvdataParser:
    """解析 jgvdata 的 WordPress 搜索页和文章详情页。"""

    source_name = "jgvdata"
    base_url = "https://jgvdata.com"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        """解析 jgvdata 文章列表。"""
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[MetadataSearchResult] = []
        seen: set[str] = set()
        for article in soup.select("article.mg-posts-sec-post"):
            link = article.select_one("a.link-div[href]")
            code_node = article.select_one(".mg-content p")
            title_node = article.select_one("h4.entry-title a")
            if not isinstance(link, Tag) or not isinstance(title_node, Tag):
                continue
            code = cls._first_line(code_node.get_text(" ", strip=True) if isinstance(code_node, Tag) else "")
            if not code or not _CODE_PATTERN.fullmatch(code) or code in seen:
                continue
            title = cls._clean_text(title_node.get_text(" ", strip=True))
            if not title:
                continue
            seen.add(code)
            results.append(
                MetadataSearchResult(
                    source=cls.source_name,
                    source_id=code,
                    category=cls.category,
                    title=title,
                    release_date=cls._date(article.get_text(" ", strip=True)),
                    image_urls=cls._images(article),
                    detail_url=urljoin(f"{cls.base_url}/", str(link["href"])),
                )
            )
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        """解析 jgvdata 文章详情。"""
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("h1.title.single") or soup.select_one("h1")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)
        original_title = cls._clean_text(heading.get_text(" ", strip=True))
        fields = cls._definition_list(soup)
        release_date = cls._parse_date(fields.get("Release Date", ""))
        labels = cls._linked_labels(soup, "Label")
        title = f"{source_id} {original_title}"
        return MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            product_number=source_id,
            title=title,
            original_title=original_title,
            sort_name=title,
            forced_sort_name=title,
            overview=fields.get("Context"),
            year=release_date.year if release_date else None,
            release_date=release_date,
            genres=[],
            studios=[],
            people=[],
            tags=[MetadataNamedItem(name=value) for value in labels],
            external_ids={
                "source": cls.source_name,
                "source_id": source_id,
                "source_url": cls._detail_url(soup, source_id),
                "product_number": source_id,
                "Imdb": source_id,
            },
            poster_url=cls._poster_url(soup),
            raw_url=cls._detail_url(soup, source_id),
        )

    @classmethod
    def _detail_url(cls, soup: BeautifulSoup, source_id: str) -> str:
        canonical = soup.select_one('link[rel="canonical"][href]')
        if isinstance(canonical, Tag) and isinstance(canonical.get("href"), str) and str(canonical["href"]).startswith("http"):
            return str(canonical["href"])
        for link in soup.select("a[href]"):
            href = link.get("href")
            if isinstance(href, str) and source_id in href and href.startswith("http") and "share" not in href and "facebook" not in href and not href.startswith("mailto:"):
                return urljoin(f"{cls.base_url}/", href)
        return f"{cls.base_url}/?s={source_id}"

    @classmethod
    def _definition_list(cls, soup: BeautifulSoup) -> dict[str, str]:
        values: dict[str, str] = {}
        definition = soup.select_one("dl")
        if not isinstance(definition, Tag):
            return values
        key: str | None = None
        for node in definition.find_all(["dt", "dd"], recursive=False):
            text = cls._clean_text(node.get_text(" ", strip=True))
            if node.name == "dt":
                key = text.rstrip(":")
            elif key and text:
                values[key] = text
        return values

    @classmethod
    def _linked_labels(cls, soup: BeautifulSoup, field: str) -> list[str]:
        definition = soup.select_one("dl")
        if not isinstance(definition, Tag):
            return []
        for dt in definition.find_all("dt"):
            if cls._clean_text(dt.get_text(" ", strip=True)).rstrip(":") == field:
                dd = dt.find_next_sibling("dd")
                if isinstance(dd, Tag):
                    return cls._unique(cls._clean_text(a.get_text(" ", strip=True)) for a in dd.find_all("a"))
        return []

    @classmethod
    def _poster_url(cls, soup: BeautifulSoup) -> str | None:
        image = soup.select_one("img.wp-post-image")
        source = image.get("src") if isinstance(image, Tag) else None
        return urljoin(f"{cls.base_url}/", source) if isinstance(source, str) else None

    @classmethod
    def _images(cls, article: Tag) -> list[str]:
        values: list[str] = []
        for node in article.select(".mg-post-thumb[style]"):
            match = re.search(r"url\(['\"]?([^'\")]+)", str(node.get("style")))
            if match:
                values.append(urljoin(f"{cls.base_url}/", match.group(1)))
        return cls._unique(values)

    @staticmethod
    def _first_line(value: str) -> str:
        return value.split()[0] if value.split() else ""

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _parse_date(value: str) -> date | None:
        match = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
        return datetime.strptime(match.group(), "%Y-%m-%d").date() if match else None

    @classmethod
    def _date(cls, value: str) -> date | None:
        match = _DATE_PATTERN.search(value)
        if not match:
            return None
        try:
            return datetime.strptime(" ".join(match.groups()), "%b %d %Y").date()
        except ValueError:
            return None

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not _CODE_PATTERN.fullmatch(source_id):
            raise ValueError("jgvdata source_id 格式无效")
