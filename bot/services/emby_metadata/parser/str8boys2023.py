import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from bs4 import BeautifulSoup, Tag
from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate, MetadataNamedItem, MetadataPerson, MetadataSearchResult


class Str8BoysParser:
    source_name = "str8boys2023"; 
    base_url = "https://str8boys2023.com/Store"; 
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @staticmethod
    def _clean(value: str) -> str: return " ".join(value.split())

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select('a[href*="detail.php"]'):
            sid = parse_qs(urlparse(str(link.get("href"))).query).get("keywords", [""])[0]; title = cls._clean(link.get_text(" ", strip=True))
            if sid and title: return [MetadataSearchResult(source=cls.source_name, source_id=sid, category=cls.category, title=title, detail_url=cls.detail_url(sid))]
        return []

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        soup = BeautifulSoup(html, "html.parser"); heading = soup.select_one("h1")
        if not isinstance(heading, Tag): raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)
        fields = {}
        for dt in soup.select("dl dt"):
            dd = dt.find_next_sibling("dd")
            if isinstance(dd, Tag): fields[cls._clean(dt.get_text(" ", strip=True))] = cls._clean(dd.get_text(" ", strip=True))
        number = fields.get("品番", source_id); title = cls._clean(heading.get_text(" ", strip=True)); result_title = f"{number} {title}"; release = None
        match = re.search(r"\d{4}/\d{1,2}/\d{1,2}", fields.get("公開日", ""))
        if match: release = datetime.strptime(match.group(), "%Y/%m/%d").date()
        tags = [x.strip() for x in re.split(r"[,，]", fields.get("MODEL TYPE", "")) if x.strip()] + [fields.get("SERIES", ""), fields.get("PLAY LIST", "")]
        image = soup.select_one(f'img[src*="/{number}/0s.jpg"]') or soup.select_one("img.ListThumImg01")
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, year=release.year if release else None, release_date=release, studios=[MetadataNamedItem(name=fields["レーベル"])] if fields.get("レーベル") else [], people=[MetadataPerson(name=fields["MODEL NAME"])] if fields.get("MODEL NAME") else [], tags=[MetadataNamedItem(name=x) for x in dict.fromkeys(x for x in tags if x)], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number}, poster_url=str(image["src"]) if isinstance(image, Tag) else None, raw_url=cls.detail_url(source_id), parse_report={"source_html_fields": fields})

    @classmethod
    def detail_url(cls, source_id: str) -> str: return f"{cls.base_url}/detail.php?did=546&cid=1&scid=&avid=&keywords={source_id}"
