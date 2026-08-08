import re
from collections.abc import Iterable
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataPerson,
    MetadataSearchResult,
)

_DETAIL_PATH = re.compile(r"^/product/detail/(\d+)(?:[/?#]|$)")
_DATE_PATTERN = re.compile(r"(\d{4})[./-](\d{2})[./-](\d{2})")


class CkDownloadParser:
    """只负责解析 ck-download 的搜索结果页和商品详情页。"""

    source_name = "ck-download"
    base_url = "https://www.ck-download.com"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        """解析搜索结果页的基础信息，不请求商品详情页。"""
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        links = soup.select("#Contents.list_page ul.title_list > li > a[href*='/product/detail/']")
        if not links:
            links = soup.select('a[href*="/product/detail/"]')

        results: list[MetadataSearchResult] = []
        seen_ids: set[str] = set()
        for link in links:
            href = link.get("href")
            if not isinstance(href, str):
                continue
            match = _DETAIL_PATH.match(urlparse(href).path)
            if match is None:
                continue
            source_id = match.group(1)
            if source_id in seen_ids:
                continue
            title = cls._search_result_title(link)
            if not title:
                continue
            seen_ids.add(source_id)
            results.append(
                MetadataSearchResult(
                    source=cls.source_name,
                    source_id=source_id,
                    category=cls.category,
                    title=title,
                    release_date=cls._search_result_date(link),
                    price_yen=cls._search_result_price(link),
                    statuses=cls._search_result_statuses(link),
                    image_urls=cls._search_result_images(link),
                    detail_url=urljoin(f"{cls.base_url}/", href),
                )
            )
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        """解析商品标题、简介、标签、演员、封面等元数据。"""
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("#Contents.detail_page > h3") or soup.select_one(".detail_page > h3")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)

        original_title = cls._clean_text(heading.get_text(" ", strip=True))
        fields = cls._parse_product_fields(soup)
        product_number = fields.get("プロダクトナンバー") or None
        display_title = f"{product_number} {original_title}" if product_number else original_title
        release_date = cls._parse_release_date(soup)
        dvd_year = cls._parse_year(fields.get("DVD発売年"))
        play_types = cls._linked_values(soup, "プレイ内容")
        model_types = cls._linked_values(soup, "モデルタイプ")
        performers = cls._linked_values(soup, "出演モデル")
        manufacturer = fields.get("メーカー")
        labels = cls._unique(
            value
            for value in [
                *play_types,
                *model_types,
                fields.get("レーベル"),
                fields.get("DVD発売年"),
                fields.get("DVDタイトル"),
            ]
            if value
        )

        return MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            product_number=product_number,
            title=display_title,
            original_title=original_title,
            sort_name=display_title,
            forced_sort_name=display_title,
            overview=cls._parse_overview(soup),
            year=release_date.year if release_date else dvd_year,
            release_date=release_date,
            genres=[MetadataNamedItem(name=value) for value in play_types],
            studios=[MetadataNamedItem(name=manufacturer)] if manufacturer else [],
            people=[MetadataPerson(name=name) for name in performers],
            tags=[MetadataNamedItem(name=value) for value in labels],
            taglines=None,
            external_ids={
                "source": cls.source_name,
                "source_id": source_id,
                "source_url": urljoin(f"{cls.base_url}/", f"product/detail/{source_id}"),
                "product_number": product_number or "",
                "Imdb": product_number or "",
            },
            poster_url=cls._parse_poster_url(soup, source_id),
            confidence=0.0,
            raw_url=urljoin(f"{cls.base_url}/", f"product/detail/{source_id}"),
        )

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not source_id.isascii() or not source_id.isdigit():
            raise ValueError("ck-download source_id 必须是纯数字")

    @classmethod
    def _search_result_title(cls, link: Tag) -> str:
        heading = link.find(["h3", "h4", "h5"])
        target = heading if isinstance(heading, Tag) else link
        return cls._clean_text(target.get_text(" ", strip=True))

    @classmethod
    def _search_result_date(cls, link: Tag) -> date | None:
        date_node = link.select_one(".ftData .date")
        if not isinstance(date_node, Tag):
            return None
        match = _DATE_PATTERN.search(date_node.get_text(" ", strip=True))
        if match is None:
            return None
        try:
            return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date()
        except ValueError:
            return None

    @classmethod
    def _search_result_price(cls, link: Tag) -> int | None:
        price_node = link.select_one(".ftData .price strong")
        if not isinstance(price_node, Tag):
            return None
        digits = re.sub(r"[^0-9]", "", price_node.get_text(strip=True))
        return int(digits) if digits else None

    @classmethod
    def _search_result_statuses(cls, link: Tag) -> list[str]:
        return cls._unique(
            cls._clean_text(node.get_text(" ", strip=True))
            for node in link.select(".status span")
        )

    @classmethod
    def _search_result_images(cls, link: Tag) -> list[str]:
        return cls._unique(
            urljoin(f"{cls.base_url}/", source)
            for image in link.select(".slideshow img")
            if isinstance(
                (source := image.get("src") or image.get("data-src") or image.get("data-original")),
                str,
            )
        )

    @classmethod
    def _parse_product_fields(cls, soup: BeautifulSoup) -> dict[str, str]:
        known_fields = {"プロダクトナンバー", "再生時間", "メーカー", "レーベル", "DVD発売年", "DVDタイトル"}
        fields: dict[str, str] = {}
        for row in soup.select("table.prod_data tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            for index in range(0, len(cells) - 1, 2):
                key = cls._clean_text(cells[index].get_text(" ", strip=True))
                if key in known_fields:
                    fields[key] = cls._clean_text(cells[index + 1].get_text(" ", strip=True))
        return fields

    @staticmethod
    def _parse_release_date(soup: BeautifulSoup) -> date | None:
        date_node = soup.select_one(".detail_page .add_info .date")
        if not isinstance(date_node, Tag):
            return None
        match = _DATE_PATTERN.search(date_node.get_text(" ", strip=True))
        if match is None:
            return None
        try:
            return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _parse_year(value: str | None) -> int | None:
        if value is None:
            return None
        match = re.search(r"(?:19|20)\d{2}", value)
        return int(match.group()) if match else None

    @staticmethod
    def _parse_runtime(value: str | None) -> int | None:
        if value is None:
            return None
        parts = value.strip().split(":")
        if len(parts) not in {2, 3} or not all(part.isdigit() for part in parts):
            return None
        hours, minutes, seconds = (0, int(parts[0]), int(parts[1])) if len(parts) == 2 else map(int, parts)
        return hours * 60 + minutes + int(seconds >= 30)

    @classmethod
    def _linked_values(cls, soup: BeautifulSoup, label: str) -> list[str]:
        for item in soup.select(".prod_category li"):
            heading = item.find("strong")
            if not isinstance(heading, Tag) or heading.get_text(strip=True) != label:
                continue
            container = item.select_one(".item")
            if not isinstance(container, Tag):
                return []
            return cls._unique(cls._clean_text(link.get_text(" ", strip=True)) for link in container.find_all("a"))
        return []

    @classmethod
    def _parse_overview(cls, soup: BeautifulSoup) -> str | None:
        container = soup.select_one(".detail_page .intro_text")
        if not isinstance(container, Tag):
            return None
        paragraphs = [cls._clean_multiline(paragraph.get_text("\n", strip=True)) for paragraph in container.find_all("p")]
        return "\n\n".join(paragraph for paragraph in paragraphs if paragraph) or None

    @classmethod
    def _parse_poster_url(cls, soup: BeautifulSoup, source_id: str) -> str | None:
        expected_suffix = f"/{source_id}/{source_id}_1.jpg"
        for image in soup.select(".detail_page .title_photo img, .detail_page .set_photo img"):
            source = image.get("src") or image.get("data-src") or image.get("data-original")
            if isinstance(source, str) and urlparse(source).path.endswith(expected_suffix):
                return urljoin(f"{cls.base_url}/", source)
        return None

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @classmethod
    def _clean_multiline(cls, value: str) -> str:
        return "\n".join(cleaned for line in value.splitlines() if (cleaned := cls._clean_text(line)))

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))
