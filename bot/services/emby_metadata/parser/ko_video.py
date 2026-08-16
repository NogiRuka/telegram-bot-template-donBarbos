import re
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse
from bs4 import BeautifulSoup, Tag
from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate, MetadataNamedItem, MetadataPerson, MetadataSearchResult


class KoVideoParser:
    source_name = "ko-video"
    base_url = "https://ko-video.com"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @staticmethod
    def _clean(value: str) -> str:
        return " ".join(value.split())

    @classmethod
    def _image_url(cls, value: str) -> str:
        return urljoin(f"{cls.base_url}/", value.strip())

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
        for link in soup.select("a[href*='products/detail.php'][href*='product_code=']"):
            code = parse_qs(urlparse(str(link.get("href"))).query).get("product_code", [""])[0]
            code = re.sub(r"_DVD$", "", code, flags=re.I)
            title_node = link.select_one("span")
            title = cls._clean(title_node.get_text(" ", strip=True)) if isinstance(title_node, Tag) else cls._clean(link.get_text(" ", strip=True))
            if not code or not title or any(item.source_id == code for item in results):
                continue
            image = link.select_one("img")
            image_src = ""
            if isinstance(image, Tag):
                image_src = str(
                    image.get("src")
                    or image.get("data-src")
                    or image.get("data-original")
                    or ""
                )
            results.append(MetadataSearchResult(source=cls.source_name, source_id=code, category=cls.category, title=title, image_urls=[cls._image_url(image_src)] if image_src else [], detail_url=cls.detail_url(code)))
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
        maker_label = fields.get("メーカー/レーベル", "").split("/", 1)
        studio = maker_label[0].strip()
        label = maker_label[1].strip() if len(maker_label) > 1 else ""
        tags = [
            value
            for value in re.split(
                r"[/\s]+",
                f"{fields.get('シリーズ/ジャンル', '')} {fields.get('モデル', '')}",
            )
            if value
        ]
        if label:
            tags.append(label)
        overview_node = soup.select_one(".deitail_txt")
        overview = cls._overview(overview_node)
        people: list[MetadataPerson] = []
        model_section = soup.select_one(".model_performance")
        if isinstance(model_section, Tag):
            for link in model_section.select("a"):
                name_node = link.select_one("span")
                name = cls._clean(name_node.get_text(" ", strip=True)) if isinstance(name_node, Tag) else cls._clean(link.get("alt", ""))
                image_node = link.select_one("img")
                image_src = image_node.get("src", "") if isinstance(image_node, Tag) else ""
                if name:
                    people.append(MetadataPerson(name=name, image_url=cls._image_url(image_src) if image_src else None))
        cast_match = re.search(r"CAST\s+(.+?)(?:\s+ほか|$)", overview or "")
        if cast_match and not people:
            people.extend(MetadataPerson(name=cls._clean(name)) for name in cast_match.group(1).split("|") if cls._clean(name))
        unique_people: list[MetadataPerson] = []
        seen_people: set[str] = set()
        for person in people:
            if person.name.casefold() not in seen_people:
                unique_people.append(person)
                seen_people.add(person.name.casefold())
        poster = soup.select_one(f'img[src*="{number}_DVD.jpg"]')
        result_title = f"{number} {title}"
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, overview=overview, year=release.year if release else None, release_date=release, studios=[MetadataNamedItem(name=studio)] if studio else [], people=unique_people, tags=[MetadataNamedItem(name=x) for x in dict.fromkeys(tags)], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(number), "product_number": number, "Imdb": number}, poster_url=cls._image_url(str(poster["src"])) if isinstance(poster, Tag) else None, raw_url=cls.detail_url(number), parse_report={"source_html_fields": fields, "overview": overview, "people": [person.model_dump(exclude_none=True) for person in unique_people], "label": label})

    @classmethod
    def detail_url(cls, source_id: str) -> str:
        return f"{cls.base_url}/products/detail.php?product_code={source_id}_DVD"
