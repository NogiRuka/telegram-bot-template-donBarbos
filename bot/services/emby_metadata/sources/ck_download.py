import re
from collections.abc import Iterable
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.auth.cookie_manager import CookieManager
from bot.services.emby_metadata.matching import calculate_confidence
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate, MetadataPerson
from bot.services.emby_metadata.sources.base import (
    MetadataSource,
    MetadataSourceHTTPError,
    MetadataSourceNetworkError,
    MetadataSourceParseError,
)

_DETAIL_PATH = re.compile(r"^/product/detail/(\d+)(?:[/?#]|$)")
_DATE_PATTERN = re.compile(r"(\d{4})[./-](\d{2})[./-](\d{2})")


class CkDownloadSource(MetadataSource):
    """ck-download 关键词搜索和商品详情适配器。"""

    name = "ck_download"
    category = MediaLibraryCategory.JAPANESE_KOREAN
    base_url = "https://www.ck-download.com"

    def __init__(self, timeout_seconds: float = 15.0, cookie_manager: CookieManager | None = None) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {
            "User-Agent": "EmbyMetadataManager/1.0 (+private metadata lookup)",
            "Accept-Language": "ja,en;q=0.8",
        }
        cookie = (cookie_manager or CookieManager()).get_cookie(self.name)
        if cookie:
            self._headers["Cookie"] = cookie

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataCandidate]:
        """使用站点关键词表单搜索，并按匹配置信度返回详情候选。"""
        search_keyword = keyword.strip()
        if limit <= 0 or not search_keyword:
            return []

        html = await self._request(
            "/product/search",
            method="POST",
            data={"kw": search_keyword, "kw_opt": "1", "only_nm": "0"},
        )
        summaries = self.parse_search_results(html, limit)
        candidates: list[MetadataCandidate] = []
        for source_id, summary_title in summaries:
            candidate = await self.fetch_detail(source_id)
            candidate.confidence = calculate_confidence(
                search_keyword,
                candidate.title or summary_title,
                candidate.product_number,
            )
            candidates.append(candidate)
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        """获取并解析指定商品详情。"""
        self._validate_source_id(source_id)
        html = await self._request(f"/product/detail/{source_id}")
        return self.parse_detail(html, source_id)

    async def _request(
        self,
        path: str,
        method: str = "GET",
        data: dict[str, str] | None = None,
    ) -> str:
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        try:
            async with aiohttp.ClientSession(timeout=self._timeout, headers=self._headers) as session:
                async with session.request(method, url, data=data) as response:
                    if response.status >= 400:
                        message = f"HTTP {response.status}: {response.reason}"
                        raise MetadataSourceHTTPError(message, self.name)
                    return await response.text()
        except MetadataSourceHTTPError:
            raise
        except (aiohttp.ClientError, TimeoutError) as error:
            raise MetadataSourceNetworkError(str(error), self.name) from error

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[tuple[str, str]]:
        """从搜索结果中的商品详情链接提取站内 ID 和标题。"""
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[tuple[str, str]] = []
        seen_ids: set[str] = set()
        for link in soup.select('a[href*="/product/detail/"]'):
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
            results.append((source_id, title))
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        """按详情页固定区域解析可写入 Emby 的元数据。"""
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("#Contents.detail_page > h3") or soup.select_one(".detail_page > h3")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.name)

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
            source=cls.name,
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
            genres=play_types,
            studios=[manufacturer] if manufacturer else [],
            people=[MetadataPerson(name=name) for name in performers],
            labels=labels,
            poster_url=cls._parse_poster_url(soup, source_id),
            runtime_minutes=cls._parse_runtime(fields.get("再生時間")),
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
            source = image.get("src")
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
