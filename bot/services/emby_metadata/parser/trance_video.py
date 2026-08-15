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
        for card in soup.select(".title_list > li"):
            link = card.select_one('a[href^="/product/detail/"]')
            heading = card.select_one("h4")
            if not isinstance(link, Tag) or not isinstance(heading, Tag):
                continue
            sid = str(link["href"]).rstrip("/").rsplit("/", 1)[-1]
            title = cls._clean(heading.get_text(" ", strip=True))
            if not re.fullmatch(r"\d+", sid) or not title or any(x.source_id == sid for x in results):
                continue
            image = card.select_one("img")
            image_src = ""
            if isinstance(image, Tag):
                image_src = str(
                    image.get("src")
                    or image.get("data-src")
                    or image.get("data-original")
                    or ""
                )
            date_node = card.select_one(".ftData .date")
            date_match = re.search(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", date_node.get_text(" ", strip=True) if isinstance(date_node, Tag) else "")
            price_node = card.select_one(".ftData .price")
            price_match = re.search(r"[\d,]+", price_node.get_text(" ", strip=True) if isinstance(price_node, Tag) else "")
            results.append(MetadataSearchResult(source=cls.source_name, source_id=sid, category=cls.category, title=title, release_date=datetime.strptime(date_match.group(), "%Y.%m.%d").date() if date_match else None, price_yen=int(price_match.group().replace(",", "")) if price_match else None, image_urls=[urljoin(cls.base_url + "/", image_src.strip())] if image_src else [], detail_url=cls.detail_url(sid)))
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
        product_category = soup.select_one(".prod_category")
        studio = ""
        tags = []
        if isinstance(product_category, Tag):
            for row in product_category.select("li"):
                label = cls._clean(row.select_one("strong").get_text(" ", strip=True)) if isinstance(row.select_one("strong"), Tag) else ""
                values = [cls._clean(a.get_text(" ", strip=True)) for a in row.select(".item a") if cls._clean(a.get_text(" ", strip=True))]
                if label == "メーカー":
                    studio = values[0] if values else ""
                elif label in {"レーベル", "カテゴリ"}:
                    tags.extend(values)
            tags = list(dict.fromkeys(tag for tag in tags if tag.upper() != "MORE"))
        overview_node = soup.select_one(".intro_text")
        overview = cls._overview(overview_node)
        price_node = soup.select_one(".detail_page .price strong")
        price_match = re.search(r"[\d,]+", price_node.get_text(" ", strip=True)) if isinstance(price_node, Tag) else None
        price = int(price_match.group().replace(",", "")) if price_match else None
        image = soup.select_one(f'img[src*="{number}_1.jpg"]') or soup.select_one("img[src*='/picture/parent/']")
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, overview=overview, release_date=release, year=release.year if release else None, price_yen=price, studios=[MetadataNamedItem(name=studio)] if studio else [], tags=[MetadataNamedItem(name=x) for x in tags], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number}, poster_url=urljoin(cls.base_url + "/", str(image["src"])) if isinstance(image, Tag) else None, raw_url=cls.detail_url(source_id), parse_report={"source_html_fields": fields, "overview": overview, "price_yen": price, "studio": studio, "tags": tags})

    @classmethod
    def detail_url(cls, source_id: str) -> str: return f"{cls.base_url}/product/detail/{source_id}"
