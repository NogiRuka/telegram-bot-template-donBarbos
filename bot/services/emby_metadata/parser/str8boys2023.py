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
    def _source_id(detail_id: str, product_number: str) -> str:
        """组合详情页 ID 和作品番号，避免不同详情入口互相串页。"""
        return f"{detail_id}:{product_number}"

    @staticmethod
    def _source_parts(source_id: str) -> tuple[str | None, str]:
        """拆分内部来源 ID；纯作品番号不包含详情页 ID。"""
        if ":" not in source_id:
            return None, source_id
        detail_id, product_number = source_id.split(":", 1)
        return detail_id or None, product_number

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
            product_number = query.get("keywords", [""])[0].strip()
            detail_id = query.get("did", [""])[0].strip()
            if not product_number or not detail_id:
                continue
            sid = cls._source_id(detail_id, product_number)
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
        _, product_number = cls._source_parts(source_id)
        number = fields.get("品番", product_number); title = cls._clean(heading.get_text(" ", strip=True)); result_title = f"{number} {title}"; release = None
        match = re.search(r"\d{4}/\d{1,2}/\d{1,2}", fields.get("公開日", ""))
        if match: release = datetime.strptime(match.group(), "%Y/%m/%d").date()
        tags = [x.strip() for x in re.split(r"[,，]", fields.get("MODEL TYPE", "")) if x.strip()] + [fields.get("SERIES", ""), fields.get("PLAY LIST", "")]
        overview_node = soup.select_one(".detailtextblock .cp_container p")
        overview = cls._overview(overview_node)
        price_node = soup.select_one(".detail-price-checkbox .Price")
        price_match = re.search(r"[\d,]+", price_node.get_text(" ", strip=True) if isinstance(price_node, Tag) else "")
        price = int(price_match.group().replace(",", "")) if price_match else None
        poster_urls = cls._poster_urls(soup, number)
        return MetadataCandidate(source=cls.source_name, source_id=source_id, category=cls.category, product_number=number, title=result_title, original_title=title, sort_name=result_title, forced_sort_name=result_title, overview=overview, year=release.year if release else None, release_date=release, price_yen=price, studios=[MetadataNamedItem(name=fields["レーベル"])] if fields.get("レーベル") else [], people=[MetadataPerson(name=fields["MODEL NAME"])] if fields.get("MODEL NAME") else [], tags=[MetadataNamedItem(name=x) for x in dict.fromkeys(x for x in tags if x)], external_ids={"source": cls.source_name, "source_id": source_id, "source_url": cls.detail_url(source_id), "product_number": number, "Imdb": number}, poster_url=poster_urls[0] if poster_urls else None, poster_urls=poster_urls, raw_url=cls.detail_url(source_id), parse_report={"source_html_fields": fields, "overview": overview, "price": price})

    @classmethod
    def _poster_urls(cls, soup: BeautifulSoup, product_number: str) -> list[str]:
        """提取当前作品的主封面与样本图，排除相关推荐作品的图片。"""
        image_pattern = re.compile(
            rf"/images/{re.escape(product_number)}/\d+s\.jpg$",
            re.IGNORECASE,
        )
        return list(dict.fromkeys(
            urljoin(cls.base_url + "/", source.strip())
            for image in soup.select("img[src]")
            if isinstance((source := image.get("src")), str)
            and image_pattern.search(urlparse(source).path)
        ))

    @classmethod
    def detail_url(cls, source_id: str) -> str:
        """根据来源 ID 生成对应详情页链接。"""
        detail_id, product_number = cls._source_parts(source_id)
        if not detail_id:
            raise ValueError("str8boys2023 详情抓取缺少搜索结果中的 did")
        return f"{cls.base_url}/detail.php?did={detail_id}&cid=1&scid=&avid=&keywords={product_number}"
