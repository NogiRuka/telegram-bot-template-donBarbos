import re
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate, MetadataNamedItem, MetadataSearchResult


class KoTubeParser:
    source_name = "ko-tube"; 
    base_url = "https://www.ko-tube.com"; 
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @staticmethod
    def _clean(value: str) -> str: return " ".join(value.split())

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        soup = BeautifulSoup(html, "html.parser"); results = []
        for link in soup.select('a[href*="/product/index/"],a[href*="/package/index/"]'):
            match = re.search(r"/(product|package)/index(?:2)?/(\d+)", str(link.get("href")))
            if not match: continue
            sid = match.group(2) if match.group(1) == "product" else f"KT-{match.group(2)}"; title = cls._clean(link.get_text(" ", strip=True))
            if not title or any(x.source_id == sid for x in results): continue
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
            if len(cells) >= 2 and cells[0].name == "th": fields[cls._clean(cells[0].get_text(" ", strip=True))] = cls._clean(cells[1].get_text(" ", strip=True))
        number = next((cls._clean(cells[1].get_text(" ", strip=True)) for tr in soup.select("table tr") if (cells := tr.find_all(["th", "td"])) and len(cells) >= 2 and cls._clean(cells[0].get_text(" ", strip=True)) == "作品番号"), source_id)
        if source_id.upper().startswith("KT-"):
            cover = soup.select_one('img[src*="_C.jpg"]'); match = re.search(r"(\d{2}-\d{2}-\d{4}(?:-\d{2})?)_C", str(cover.get("src")) if isinstance(cover, Tag) else "")
            number = match.group(1) if match else number
        title = cls._clean(heading.get_text(" ", strip=True)); result_title = f"{number} {title}"; release = None
        match = re.search(r"(\d{4})年(\d{1,2})月", fields.get("DVD発売", ""))
        if match: release = date(int(match.group(1)), int(match.group(2)), 1)
        studio = fields.get("メーカー"); tags = [x for x in re.split(r"\s+", fields.get("プレイ", "") + " " + fields.get("モデル", "")) if x]
        image = soup.select_one(f'img[src*="{number}_C.jpg"]') or soup.select_one("img[src*='/picture/parent/']")
        report = {"source_html_fields": fields, "is_package": source_id.upper().startswith("KT-"), "child_product_links": list(dict.fromkeys(str(a.get("href")) for a in soup.select('a[href*="/product/index2/"]')))}
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, year=release.year if release else None, release_date=release, studios=[MetadataNamedItem(name=studio)] if studio else [], tags=[MetadataNamedItem(name=x) for x in dict.fromkeys(tags)], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number}, poster_url=urljoin(cls.base_url + "/", str(image["src"])) if isinstance(image, Tag) else None, raw_url=cls.detail_url(source_id), parse_report=report)

    @classmethod
    def detail_url(cls, source_id: str) -> str: return f"{cls.base_url}/package/index/{source_id[3:]}" if source_id.upper().startswith("KT-") else f"{cls.base_url}/product/index/{source_id}"
