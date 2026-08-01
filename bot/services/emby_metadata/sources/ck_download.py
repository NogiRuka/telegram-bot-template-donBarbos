import re
from collections.abc import Iterable
from datetime import date, datetime
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.matching import calculate_confidence, extract_product_number
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate
from bot.services.emby_metadata.sources.base import (
    MetadataSource,
    MetadataSourceHTTPError,
    MetadataSourceNetworkError,
    MetadataSourceParseError,
)

_DETAIL_PATH = re.compile(r"^/product/detail/(\d+)(?:[/?#]|$)")
_DATE_PATTERN = re.compile(r"(\d{4})[./-](\d{2})[./-](\d{2})")
_PRICE_MARKERS = ("販売価格", "カートに入れる")
_EXCLUDED_OVERVIEW_TEXT = ("ログイン", "会員登録", "お気に入り", "税込", "販売価格")


class CkDownloadSource(MetadataSource):
    name = "ck_download"
    category = MediaLibraryCategory.JAPANESE_KOREAN
    base_url = "https://ck-download.com"

    def __init__(self, timeout_seconds: float = 15.0) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._headers = {
            "User-Agent": "EmbyMetadataManager/1.0 (+private metadata lookup)",
            "Accept-Language": "ja,en;q=0.8",
        }

    async def search(self, keyword: str, limit: int = 10) -> list[MetadataCandidate]:
        if limit <= 0:
            return []
        search_keyword = extract_product_number(keyword) or keyword.strip()
        if not search_keyword:
            return []

        html = await self._request("/product/search", params={"kw": search_keyword, "only_nm": "0", "kw_opt": "1"})
        summaries = self.parse_search_results(html, limit)
        candidates: list[MetadataCandidate] = []
        for source_id, summary_title in summaries:
            candidate = await self.fetch_detail(source_id)
            candidate.confidence = calculate_confidence(
                keyword,
                candidate.title or summary_title,
                candidate.external_ids.get("CkDownload"),
            )
            candidates.append(candidate)
        return sorted(candidates, key=lambda item: item.confidence, reverse=True)

    async def fetch_detail(self, source_id: str) -> MetadataCandidate:
        self._validate_source_id(source_id)
        html = await self._request(f"/product/detail/{source_id}")
        return self.parse_detail(html, source_id)

    async def _request(self, path: str, params: dict[str, str] | None = None) -> str:
        url = urljoin(f"{self.base_url}/", path.lstrip("/"))
        try:
            async with aiohttp.ClientSession(timeout=self._timeout, headers=self._headers) as session:
                async with session.get(url, params=params) as response:
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
        soup = BeautifulSoup(html, "html.parser")
        results: list[tuple[str, str]] = []
        seen_ids: set[str] = set()
        for link in soup.select('a[href*="/product/detail/"]'):
            href = link.get("href")
            if not isinstance(href, str):
                continue
            path = href.removeprefix(cls.base_url)
            match = _DETAIL_PATH.match(path)
            if match is None:
                continue
            source_id = match.group(1)
            if source_id in seen_ids:
                continue
            title = " ".join(link.get_text(" ", strip=True).split())
            if not title:
                continue
            seen_ids.add(source_id)
            results.append((source_id, title))
            if len(results) >= max(limit, 0):
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find("h3")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.name)

        title = " ".join(heading.get_text(" ", strip=True).split())
        fields = cls._parse_product_fields(soup)
        product_number = fields.get("プロダクトナンバー")
        release_date = cls._parse_release_date(soup)
        dvd_year = cls._parse_year(fields.get("DVD発売年"))
        play_types = cls._linked_values(soup, "プレイ内容")
        model_types = cls._linked_values(soup, "モデルタイプ")
        manufacturer = fields.get("メーカー")
        label = fields.get("レーベル")
        labels = cls._unique(value for value in [label, *model_types, *play_types] if value)

        return MetadataCandidate(
            source=cls.name,
            source_id=source_id,
            category=cls.category,
            title=title,
            original_title=fields.get("DVDタイトル") or None,
            overview=cls._parse_overview(heading),
            year=release_date.year if release_date else dvd_year,
            release_date=release_date,
            genres=play_types,
            studios=[manufacturer] if manufacturer else [],
            external_ids={"CkDownload": product_number} if product_number else {},
            poster_url=cls._parse_poster_url(soup),
            raw_url=urljoin(f"{cls.base_url}/", f"product/detail/{source_id}"),
            runtime_minutes=cls._parse_runtime(fields.get("再生時間")),
            labels=labels,
        )

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not source_id.isascii() or not source_id.isdigit():
            raise ValueError("ck-download source_id 必须是纯数字")

    @staticmethod
    def _parse_product_fields(soup: BeautifulSoup) -> dict[str, str]:
        known_fields = {"プロダクトナンバー", "再生時間", "メーカー", "レーベル", "DVD発売年", "DVDタイトル"}
        fields: dict[str, str] = {}
        for row in soup.select("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            for index in range(0, len(cells) - 1, 2):
                key = " ".join(cells[index].get_text(" ", strip=True).split())
                if key in known_fields:
                    fields[key] = " ".join(cells[index + 1].get_text(" ", strip=True).split())
        return fields

    @staticmethod
    def _parse_release_date(soup: BeautifulSoup) -> date | None:
        for text in soup.stripped_strings:
            match = _DATE_PATTERN.search(text)
            if match is not None and ("UP" in text or len(text.strip()) <= 16):
                try:
                    return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date()
                except ValueError:
                    continue
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

    @staticmethod
    def _linked_values(soup: BeautifulSoup, label: str) -> list[str]:
        label_node = soup.find(string=lambda text: text is not None and text.strip() == label)
        if label_node is None or not isinstance(label_node.parent, Tag):
            return []
        container = label_node.parent.parent if isinstance(label_node.parent.parent, Tag) else label_node.parent
        values = [" ".join(link.get_text(" ", strip=True).split()) for link in container.find_all("a")]
        return CkDownloadSource._unique(value for value in values if value)

    @staticmethod
    def _parse_overview(heading: Tag) -> str | None:
        paragraphs: list[str] = []
        for element in heading.find_all_next(["p", "div"]):
            text = " ".join(element.get_text(" ", strip=True).split())
            if any(marker in text for marker in _PRICE_MARKERS):
                break
            if not text or _DATE_PATTERN.search(text) or any(excluded in text for excluded in _EXCLUDED_OVERVIEW_TEXT):
                continue
            if element.find_parent(["nav", "header", "footer", "table"]):
                continue
            if element.name == "div" and element.find(["p", "div"], recursive=False):
                continue
            paragraphs.append(text)
        return "\n".join(CkDownloadSource._unique(paragraphs)) or None

    @classmethod
    def _parse_poster_url(cls, soup: BeautifulSoup) -> str | None:
        selectors = (".product-image img", ".product_image img", ".main-image img", "#main_image")
        for selector in selectors:
            image = soup.select_one(selector)
            if not isinstance(image, Tag):
                continue
            source = image.get("src")
            if not isinstance(source, str) or not source.strip():
                continue
            lowered = source.casefold()
            if any(marker in lowered for marker in ("logo", "banner", "spacer", "noimage", "transparent")):
                continue
            return urljoin(f"{cls.base_url}/", source)
        return None

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(values))
