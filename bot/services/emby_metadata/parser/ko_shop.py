import re
from datetime import date, datetime
from collections.abc import Iterable
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from bot.services.emby_metadata.errors import MetadataSourceParseError
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataSearchResult,
)


class KoShopParser:
    """解析 ko-shop 商品搜索页和详情页。"""

    source_name = "ko-shop"
    base_url = "https://www.ko-shop.com"
    category = MediaLibraryCategory.JAPANESE_KOREAN

    @classmethod
    def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
        """解析 ko-shop 商品列表。"""
        if limit <= 0:
            return []
        soup = BeautifulSoup(html, "html.parser")
        results: list[MetadataSearchResult] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="products/detail.php"]'):
            source_id = cls._source_id(link.get("href"))
            title_node = link.select_one(".list_title") or link.select_one("img[alt]")
            if source_id is None or source_id in seen or not isinstance(title_node, Tag):
                continue
            title = cls._clean_text(title_node.get("alt") or title_node.get_text(" ", strip=True))
            if not title:
                continue
            seen.add(source_id)
            item = link.parent if isinstance(link.parent, Tag) else link
            results.append(
                MetadataSearchResult(
                    source=cls.source_name,
                    source_id=source_id,
                    category=cls.category,
                    title=title,
                    price_yen=cls._price(item),
                    statuses=cls._statuses(item),
                    image_urls=cls._images(link),
                    detail_url=urljoin(f"{cls.base_url}/", str(link["href"])),
                )
            )
            if len(results) >= limit:
                break
        return results

    @classmethod
    def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
        """解析 ko-shop 商品详情。"""
        cls._validate_source_id(source_id)
        soup = BeautifulSoup(html, "html.parser")
        product = soup.select_one(".detail_product")
        heading = product.select_one("h2") if isinstance(product, Tag) else soup.select_one("h2")
        if not isinstance(heading, Tag) or not heading.get_text(strip=True):
            raise MetadataSourceParseError("详情页缺少作品标题", cls.source_name)
        fields = cls._fields(product if isinstance(product, Tag) else soup)
        original_title = cls._clean_text(heading.get_text(" ", strip=True))
        product_number = cls._strip_suffix(fields.get("商品コード"), "_DVD")
        title = f"{product_number} {original_title}" if product_number else original_title
        release_date = cls._parse_date(fields.get("発売日", ""))
        tags = cls._split_values(fields.get("モデルタイプ", ""))
        tags.extend(cls._linked_field_values(product if isinstance(product, Tag) else soup, "キーワード"))
        tags = cls._unique(tags)
        genres = cls._genres(soup)
        studio = fields.get("メーカー")
        return MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            product_number=product_number,
            title=title,
            original_title=original_title,
            sort_name=title,
            forced_sort_name=title,
            overview=cls._overview(soup),
            year=release_date.year if release_date else None,
            release_date=release_date,
            genres=[MetadataNamedItem(name=value) for value in genres],
            studios=[MetadataNamedItem(name=studio)] if studio else [],
            people=[],
            tags=[MetadataNamedItem(name=value) for value in tags],
            external_ids={
                "source": cls.source_name,
                "source_id": source_id,
                "source_url": cls._detail_url(source_id),
                "product_number": product_number or "",
                "Imdb": product_number or source_id,
            },
            poster_url=cls._poster_url(soup),
            raw_url=cls._detail_url(source_id),
        )

    @classmethod
    def _fields(cls, container: Tag | BeautifulSoup) -> dict[str, str]:
        fields: dict[str, str] = {}
        for dt in container.select("dl dt"):
            dd = dt.find_next_sibling("dd")
            if isinstance(dd, Tag):
                fields[cls._clean_text(dt.get_text(" ", strip=True))] = cls._clean_text(dd.get_text(" ", strip=True)).lstrip(": ")
        return fields

    @classmethod
    def _linked_field_values(cls, container: Tag | BeautifulSoup, field_name: str) -> list[str]:
        """提取详情字段下的链接值，例如キーワード的多个标签。"""
        values: list[str] = []
        for dt in container.select("dl dt"):
            if cls._clean_text(dt.get_text(" ", strip=True)) != field_name:
                continue
            dd = dt.find_next_sibling("dd")
            if not isinstance(dd, Tag):
                continue
            values.extend(
                cls._clean_text(link.get_text(" ", strip=True))
                for link in dd.select("a")
                if cls._clean_text(link.get_text(" ", strip=True))
            )
        return cls._unique(values)

    @classmethod
    def _overview(cls, soup: BeautifulSoup) -> str | None:
        """提取商品説明正文，排除预告视频和页面说明文字。"""
        heading = next(
            (
                node
                for node in soup.select(".ma_b30 > h2")
                if cls._clean_text(node.get_text(" ", strip=True)) == "商品説明"
            ),
            None,
        )
        container = heading.parent if isinstance(heading, Tag) else None
        if not isinstance(container, Tag):
            return None
        for node in container.select("video, script, style, .icon_exp"):
            if node.name == "video" and isinstance(node.parent, Tag):
                node = node.parent
            node.decompose()
        for node in container.select("h2, p"):
            if cls._clean_text(node.get_text(" ", strip=True)) in {
                "予告映像",
                "※通信環境により再生まで時間がかかる場合があります",
            }:
                node.decompose()
        lines = [
            cls._clean_text(line)
            for line in container.get_text("\n", strip=True).splitlines()
            if cls._clean_text(line) and cls._clean_text(line) != "商品説明"
        ]
        return "\n".join(lines) or None

    @classmethod
    def _genres(cls, soup: BeautifulSoup) -> list[str]:
        """解析商品页上的排行榜徽章，并写入 Genre。"""
        return cls._unique(
            cls._clean_text(node.get_text(" ", strip=True))
            for node in soup.select(".p13n-best-seller-badge")
            if cls._clean_text(node.get_text(" ", strip=True))
        )

    @classmethod
    def _poster_url(cls, soup: BeautifulSoup) -> str | None:
        image = soup.select_one(".detail_main_img a.fancybox[href]")
        source = image.get("href") if isinstance(image, Tag) else None
        return urljoin(f"{cls.base_url}/", str(source).split("?", 1)[0]) if isinstance(source, str) else None

    @classmethod
    def _images(cls, link: Tag) -> list[str]:
        return cls._unique(
            urljoin(f"{cls.base_url}/", str(source))
            for image in link.select("img")
            if isinstance((source := image.get("src")), str)
        )

    @staticmethod
    def _price(item: Tag) -> int | None:
        price = item.select_one(".price_list .this_red")
        if not isinstance(price, Tag):
            return None
        digits = re.sub(r"[^0-9]", "", price.get_text(" ", strip=True))
        return int(digits) if digits else None

    @classmethod
    def _statuses(cls, item: Tag) -> list[str]:
        names = {
            "icon_haya": "早割作品",
            "icon_shin": "新作",
            "icon_middle_new": "新作ミドル商品",
            "icon_middle": "ミドル商品",
            "icon_outlet_new": "新作アウトレット商品",
            "icon_outlet": "アウトレット商品",
            "icon_sale": "セール商品",
            "sample_mv": "サンプル動画あり",
            "icon_coupon": "クーポン封入",
            "icon_pickup": "イチオシ",
            "icon_review": "レビュー投稿あり",
            "icon_limit": "数量限定",
            "icon_kaiwari": "買うほど割引",
            "icon_nimai": "2枚目タダ",
        }
        return cls._unique(
            names[class_name]
            for node in item.select(".list_tag [class]")
            for class_name in node.get("class", [])
            if class_name in names
        )

    @staticmethod
    def _source_id(href: object) -> str | None:
        if not isinstance(href, str):
            return None
        value = parse_qs(urlparse(href).query).get("product_id", [None])[0]
        return value if isinstance(value, str) and value.isdigit() else None

    @staticmethod
    def _detail_url(source_id: str) -> str:
        return f"https://www.ko-shop.com/products/detail.php?product_id={source_id}"

    @staticmethod
    def _clean_text(value: str) -> str:
        return " ".join(value.split())

    @staticmethod
    def _parse_date(value: str) -> date | None:
        match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", value)
        if not match:
            return None
        return datetime.strptime("-".join(match.groups()), "%Y-%m-%d").date()

    @classmethod
    def _split_values(cls, value: str) -> list[str]:
        return cls._unique(cls._clean_text(item) for item in re.split(r"[/／]", value) if cls._clean_text(item))

    @staticmethod
    def _strip_suffix(value: str | None, suffix: str) -> str | None:
        if not value:
            return None
        return re.sub(rf"{re.escape(suffix)}$", "", value, flags=re.IGNORECASE)

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    @staticmethod
    def _validate_source_id(source_id: str) -> None:
        if not source_id.isdigit():
            raise ValueError("ko-shop source_id 必须是数字")
