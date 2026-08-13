import re
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate, MetadataNamedItem, MetadataSearchResult


class TranceVideoParser:
    source_name = "trance-video"; 
    base_url = "https://www.trance-video.com"; 
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @staticmethod
    def _clean(value: str) -> str: return " ".join(value.split())

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        soup = BeautifulSoup(html, "html.parser"); results = []
        for link in soup.select('a[href^="/product/detail/"]'):
            sid = str(link["href"]).rstrip("/").rsplit("/", 1)[-1]; title = cls._clean(link.get_text(" ", strip=True))
            if not re.fullmatch(r"\d+", sid) or not title or any(x.source_id == sid for x in results): continue
            results.append(MetadataSearchResult(source=cls.source_name, source_id=sid, category=cls.category, title=title, detail_url=cls.detail_url(sid)))
            if len(results) >= limit: break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        soup = BeautifulSoup(html, "html.parser"); heading = soup.select_one("h3")
        if not isinstance(heading, Tag): raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)
        fields = {}
        for tr in soup.select("table tr"):
            cells = tr.find_all(["th", "td"])
            for i in range(0, len(cells) - 1, 2): fields[cls._clean(cells[i].get_text(" ", strip=True))] = cls._clean(cells[i + 1].get_text(" ", strip=True))
        number = fields.get("作品ID", source_id); title = cls._clean(heading.get_text(" ", strip=True)); result_title = f"{number} {title}"
        release = None; match = re.search(r"\d{4}\.\d{1,2}\.\d{1,2}", fields.get("掲載日", ""))
        if match: release = datetime.strptime(match.group().replace(".", "/"), "%Y/%m/%d").date()
        detail = soup.select_one(".detail_page") or soup
        tags = list(dict.fromkeys(cls._clean(a.get_text(" ", strip=True)) for a in detail.select('a[href*="play_type"],a[href*="label"]')))
        image = soup.select_one(f'img[src*="{number}_1.jpg"]') or soup.select_one("img[src*='/picture/parent/']")
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, year=release.year if release else None, release_date=release, tags=[MetadataNamedItem(name=x) for x in tags], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number}, poster_url=urljoin(cls.base_url + "/", str(image["src"])) if isinstance(image, Tag) else None, raw_url=cls.detail_url(source_id), parse_report={"source_html_fields": fields})

    @classmethod
    def detail_url(cls, source_id: str) -> str: return f"{cls.base_url}/product/detail/{source_id}"
