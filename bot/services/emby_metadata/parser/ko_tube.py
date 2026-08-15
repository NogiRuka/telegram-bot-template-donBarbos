import re
from datetime import date
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataPerson,
    MetadataSearchResult,
)


class KoTubeParser:
    source_name = "ko-tube"
    base_url = "https://www.ko-tube.com"
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

    @staticmethod
    def _price(node: Tag | None) -> int | None:
        if not isinstance(node, Tag):
            return None
        match = re.search(r"[\d,]+", node.get_text(" ", strip=True))
        return int(match.group().replace(",", "")) if match else None

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[MetadataSearchResult] = []
        for card in soup.select(".title_list > li"):
            link = card.select_one('a[href*="/product/index/"],a[href*="/package/index/"]')
            if not isinstance(link, Tag):
                continue
            match = re.search(r"/(product|package)/index(?:2)?/(\d+)", str(link.get("href")))
            heading = card.select_one("h4")
            if not match or not isinstance(heading, Tag):
                continue
            source_id = match.group(2) if match.group(1) == "product" else f"KT-{match.group(2)}"
            title = cls._clean(heading.get_text(" ", strip=True))
            if not title or any(item.source_id == source_id for item in results):
                continue
            image = card.select_one("img")
            image_src = image.get("src", "") if isinstance(image, Tag) else ""
            price_node = card.select_one(".price li.gold, .price li.reg")
            statuses = [cls._clean(img.get("alt", "")) for img in card.select(".status img") if img.get("alt")]
            results.append(MetadataSearchResult(
                source=cls.source_name,
                source_id=source_id,
                category=cls.category,
                title=title,
                price_yen=cls._price(price_node),
                statuses=statuses,
                image_urls=[cls._image_url(image_src)] if image_src else [],
                detail_url=cls.detail_url(source_id),
            ))
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("h3")
        if not isinstance(heading, Tag):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)

        fields: dict[str, str] = {}
        for row in soup.select(".movie_data tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) >= 2:
                fields[cls._clean(cells[0].get_text(" ", strip=True))] = cls._clean(cells[1].get_text(" ", strip=True))

        number = fields.get("作品番号", source_id)
        if source_id.upper().startswith("KT-"):
            cover = soup.select_one('.pack_photo img[src*="_C.jpg"]')
            match = re.search(r"(\d{2}-\d{2}-\d{4})_C", str(cover.get("src")) if isinstance(cover, Tag) else "")
            number = match.group(1) if match else number
        title = cls._clean(heading.get_text(" ", strip=True))
        result_title = f"{number} {title}"

        release = None
        date_node = soup.select_one(".base_data .date, .pack_data .date")
        date_value = cls._clean(date_node.get_text(" ", strip=True)) if isinstance(date_node, Tag) else fields.get("DVD発売", "")
        date_match = re.search(r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})?", date_value)
        if date_match:
            release = date(int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3) or 1))

        studio = fields.get("メーカー", "")
        label = fields.get("レーベル", "")
        tags = [value for value in re.split(r"\s+", f"{fields.get('プレイ', '')} {fields.get('モデル', '')} {label}") if value]
        overview_node = soup.select_one(".intro_text") or soup.select_one(".sub_data > p:not(.dousa)")
        overview = cls._overview(overview_node)
        price = cls._price(soup.select_one(".single_price .price .gold, .pack_price .price .gold"))
        people = []
        model_list = soup.select_one("#model_list")
        if isinstance(model_list, Tag):
            for item in model_list.select("li"):
                name_node = item.select_one("h6")
                link = item.select_one('a[href*="/search/index?ml"]')
                name = cls._clean(name_node.get_text(" ", strip=True)) if isinstance(name_node, Tag) else ""
                image = link.select_one("img") if isinstance(link, Tag) else None
                image_src = image.get("src", "") if isinstance(image, Tag) else ""
                if name:
                    people.append(MetadataPerson(name=name, image_url=cls._image_url(image_src) if image_src else None))
        image = soup.select_one(f'img[src*="{number}_C.jpg"]') or soup.select_one("img[src*='/picture/parent/']")
        report = {
            "source_html_fields": fields,
            "is_package": source_id.upper().startswith("KT-"),
            "child_product_links": list(dict.fromkeys(str(link.get("href")) for link in soup.select('a[href*="/product/index2/"]'))),
            "overview": overview,
            "price": price,
            "date": date_value,
            "label": label,
            "people": people,
        }
        return MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            product_number=number,
            title=result_title,
            original_title=title,
            sort_name=result_title,
            forced_sort_name=result_title,
            overview=overview,
            year=release.year if release else None,
            release_date=release,
            price_yen=price,
            studios=[MetadataNamedItem(name=studio)] if studio else [],
            people=people,
            tags=[MetadataNamedItem(name=name) for name in dict.fromkeys(tags)],
            external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number},
            poster_url=cls._image_url(str(image.get("src"))) if isinstance(image, Tag) else None,
            raw_url=cls.detail_url(source_id),
            parse_report=report,
        )

    @classmethod
    def detail_url(cls, source_id: str) -> str:
        return f"{cls.base_url}/package/index/{source_id[3:]}" if source_id.upper().startswith("KT-") else f"{cls.base_url}/product/index/{source_id}"
