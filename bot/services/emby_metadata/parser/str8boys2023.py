import re
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse
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
    def _overview(cls, node: Tag | None) -> str | None:
        if not isinstance(node, Tag):
            return None
        for br in node.select("br"):
            br.replace_with("\n")
        lines = [cls._clean(line) for line in node.get_text("\n").splitlines()]
        return "\n".join(line for line in lines if line) or None

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for card in soup.select("li.thumbox"):
            link = card.select_one('a[href*="detail.php"]')
            if not isinstance(link, Tag):
                continue
            query = parse_qs(urlparse(str(link.get("href"))).query)
            sid = query.get("keywords", [""])[0].strip()
            title_node = card.select_one(".id-title a")
            title = cls._clean(title_node.get_text(" ", strip=True)) if isinstance(title_node, Tag) else ""
            if not sid or not title or any(item.source_id == sid for item in results):
                continue
            image = card.select_one(".photoblock img.ListThumImg01, img.ListThumImg01")
            image_src = ""
            if isinstance(image, Tag):
                image_src = str(
                    image.get("src")
                    or image.get("data-src")
                    or image.get("data-original")
                    or ""
                )
            price_node = card.select_one(".textblock")
            price_match = re.search(r"[\d,]+", price_node.get_text(" ", strip=True) if isinstance(price_node, Tag) else "")
            statuses = [cls._clean(node.get_text(" ", strip=True)) for node in card.select(".id-block-tag span") if cls._clean(node.get_text(" ", strip=True))]
            results.append(MetadataSearchResult(source=cls.source_name, source_id=sid, category=cls.category, title=title, price_yen=int(price_match.group().replace(",", "")) if price_match else None, statuses=statuses, image_urls=[image_src.strip()] if image_src else [], detail_url=cls.detail_url(sid)))
            if len(results) >= limit:
                break
        return results

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
        overview_node = soup.select_one(".detailtextblock .cp_container p")
        overview = cls._overview(overview_node)
        price_node = soup.select_one(".detail-price-checkbox .Price")
        price_match = re.search(r"[\d,]+", price_node.get_text(" ", strip=True) if isinstance(price_node, Tag) else "")
        price = int(price_match.group().replace(",", "")) if price_match else None
        image = soup.select_one(f'img[src*="/{number}/0s.jpg"]') or soup.select_one("img.ListThumImg01")
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, overview=overview, year=release.year if release else None, release_date=release, price_yen=price, studios=[MetadataNamedItem(name=fields["レーベル"])] if fields.get("レーベル") else [], people=[MetadataPerson(name=fields["MODEL NAME"])] if fields.get("MODEL NAME") else [], tags=[MetadataNamedItem(name=x) for x in dict.fromkeys(x for x in tags if x)], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number}, poster_url=urljoin(cls.base_url + "/", str(image["src"]).strip()) if isinstance(image, Tag) else None, raw_url=cls.detail_url(source_id), parse_report={"source_html_fields": fields, "overview": overview, "price": price})

    @classmethod
    def detail_url(cls, source_id: str) -> str: return f"{cls.base_url}/detail.php?did=546&cid=1&scid=&avid=&keywords={source_id}"
