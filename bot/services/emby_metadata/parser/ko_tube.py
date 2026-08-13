import re
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate, MetadataNamedItem, MetadataPerson, MetadataSearchResult


class KoTubeParser:
    source_name = "ko-tube"; 
    base_url = "https://www.ko-tube.com"; 
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @staticmethod
    def _clean(value: str) -> str: return " ".join(value.split())

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        soup = BeautifulSoup(html, "html.parser"); results = []
        for card in soup.select(".title_list > li"):
            link = card.select_one('a[href*="/product/index/"],a[href*="/package/index/"]')
            if not isinstance(link, Tag):
                continue
            match = re.search(r"/(product|package)/index(?:2)?/(\d+)", str(link.get("href")))
            if not match: continue
            heading = card.select_one("h4")
            sid = match.group(2) if match.group(1) == "product" else f"KT-{match.group(2)}"
            title = cls._clean(heading.get_text(" ", strip=True)) if isinstance(heading, Tag) else ""
            if not title or any(x.source_id == sid for x in results): continue
            image = card.select_one("img")
            image_src = ""
            if isinstance(image, Tag):
                image_src = str(
                    image.get("src")
                    or image.get("data-src")
                    or image.get("data-original")
                    or ""
                )
            results.append(MetadataSearchResult(source=cls.source_name, source_id=sid, category=cls.category, title=title, image_urls=[urljoin(cls.base_url + "/", image_src)] if image_src else [], detail_url=cls.detail_url(sid)))
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
        date_value = cls._clean((soup.select_one(".base_data .date") or Tag()).get_text(" ", strip=True)) if soup.select_one(".base_data .date") else ""
        match = re.search(r"(\d{4})[./](\d{1,2})[./](\d{1,2})", date_value)
        if match: release = date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        if release is None:
            match = re.search(r"(\d{4})年(\d{1,2})月", fields.get("DVD発売", ""))
            if match: release = date(int(match.group(1)), int(match.group(2)), 1)
        studio = fields.get("メーカー", "")
        label = fields.get("レーベル", "")
        tags = [x for x in re.split(r"\s+", fields.get("プレイ", "") + " " + fields.get("モデル", "") + " " + label) if x]
        overview_node = soup.select_one(".intro_text") or soup.select_one(".sub_data > p:not(.dousa)")
        overview = cls._clean(overview_node.get_text(" ", strip=True)) if isinstance(overview_node, Tag) else None
        price_node = soup.select_one(".single_price .price .gold strong, .pack_price .price .gold strong")
        price_match = re.search(r"[\d,]+", price_node.get_text(" ", strip=True)) if isinstance(price_node, Tag) else None
        price = int(price_match.group().replace(",", "")) if price_match else None
        people = []
        model_list = soup.select_one("#model_list")
        if isinstance(model_list, Tag):
            people = [cls._clean(node.get_text(" ", strip=True)) for node in model_list.select('a[href*="/search/index?ml"]') if cls._clean(node.get_text(" ", strip=True))]
        image = soup.select_one(f'img[src*="{number}_C.jpg"]') or soup.select_one("img[src*='/picture/parent/']")
        report = {"source_html_fields": fields, "is_package": source_id.upper().startswith("KT-"), "child_product_links": list(dict.fromkeys(str(a.get("href")) for a in soup.select('a[href*="/product/index2/"]')))}
        report.update({"overview": overview, "price": price, "date": date_value, "label": label, "people": people})
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, overview=overview, year=release.year if release else None, release_date=release, price_yen=price, studios=[MetadataNamedItem(name=studio)] if studio else [], people=[MetadataPerson(name=x) for x in people], tags=[MetadataNamedItem(name=x) for x in dict.fromkeys(tags)], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number}, poster_url=urljoin(cls.base_url + "/", str(image["src"])) if isinstance(image, Tag) else None, raw_url=cls.detail_url(source_id), parse_report=report)

    @classmethod
    def detail_url(cls, source_id: str) -> str: return f"{cls.base_url}/package/index/{source_id[3:]}" if source_id.upper().startswith("KT-") else f"{cls.base_url}/product/index/{source_id}"
