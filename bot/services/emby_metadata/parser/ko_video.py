import re
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate, MetadataNamedItem, MetadataSearchResult


class KoVideoParser:
    source_name = "ko-video"
    base_url = "https://ko-video.com"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(value.split())

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for link in soup.select('a[href*="products/detail.php?product_code="]'):
            code = parse_qs(urlparse(str(link.get("href"))).query).get("product_code", [""])[0]
            code = re.sub(r"_DVD$", "", code, flags=re.I)
            title = cls._clean(link.get_text(" ", strip=True))
            if not code or not title or any(item.source_id == code for item in results):
                continue
            results.append(MetadataSearchResult(source=cls.source_name, source_id=code, category=cls.category, title=title, detail_url=cls.detail_url(code)))
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("h2")
        if not isinstance(heading, Tag):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)
        fields = {}
        for dt in soup.select("dl dt"):
            dd = dt.find_next_sibling("dd")
            if isinstance(dd, Tag):
                fields[cls._clean(dt.get_text(" ", strip=True))] = cls._clean(dd.get_text(" ", strip=True)).lstrip(": ")
        number = re.sub(r"_DVD$", "", source_id, flags=re.I)
        title = cls._clean(heading.get_text(" ", strip=True))
        release = None
        match = re.search(r"\d{4}/\d{1,2}/\d{1,2}", fields.get("商品発売日", ""))
        if match:
            release = datetime.strptime(match.group(), "%Y/%m/%d").date()
        studio = fields.get("メーカー/レーベル", "").split("/", 1)[0].strip()
        tags = [x for x in re.split(r"[/\s]+", fields.get("シリーズ/ジャンル", "") + " " + fields.get("モデル", "")) if x]
        poster = soup.select_one(f'img[src*="{number}_DVD.jpg"]')
        result_title = f"{number} {title}"
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, year=release.year if release else None, release_date=release, studios=[MetadataNamedItem(name=studio)] if studio else [], tags=[MetadataNamedItem(name=x) for x in dict.fromkeys(tags)], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(number), "product_number": number, "Imdb": number}, poster_url=urljoin(cls.base_url + "/", poster["src"]) if isinstance(poster, Tag) else None, raw_url=cls.detail_url(number), parse_report={"source_html_fields": fields})

    @classmethod
    def detail_url(cls, source_id: str) -> str:
        return f"{cls.base_url}/products/detail.php?product_code={source_id}_DVD"
