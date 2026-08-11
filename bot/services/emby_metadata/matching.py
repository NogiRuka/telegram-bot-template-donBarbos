import re
from difflib import SequenceMatcher

_PRODUCT_NUMBER_PATTERNS = (
    re.compile(r"\b(?:NO\.)\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{2,}(?:-[A-Z]+)*-?\d+(?:-[A-Z0-9]+)?\b", re.IGNORECASE),
)


def extract_product_number(value: str) -> str | None:
    """从标题或关键词中提取常见番号。"""
    for pattern in _PRODUCT_NUMBER_PATTERNS:
        match = pattern.search(value)
        if match is not None:
            return match.group().strip()
    return None


def normalize_product_number(value: str) -> str:
    """移除番号中的大小写和分隔符差异。"""
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def normalize_search_keyword(value: str) -> str:
    """规范化数据源搜索词；GV- 是 hunk-ch 的站内前缀，不作为番号本体。"""
    keyword = value.strip()
    return re.sub(r"^GV-", "", keyword, count=1, flags=re.IGNORECASE).strip()


def is_hunk_ch_product_number(value: str) -> bool:
    normalized = normalize_product_number(value)
    # HUNK 既可能出现在 Emby 中的 GV-OAV1351，也可能只保存为 OAV1351。
    return normalized.startswith("GVOAV") or normalized.startswith("OAV")


def calculate_confidence(keyword: str, title: str, product_number: str | None) -> float:
    """按番号精确度优先、标题相似度辅助计算候选置信度。"""
    keyword_number = extract_product_number(keyword)
    if keyword_number and product_number:
        if normalize_product_number(keyword_number) == normalize_product_number(product_number):
            return 1.0

    normalized_keyword = " ".join(keyword.casefold().split())
    normalized_title = " ".join(title.casefold().split())
    if not normalized_keyword or not normalized_title:
        return 0.0

    similarity = SequenceMatcher(None, normalized_keyword, normalized_title).ratio()
    if keyword_number and product_number:
        return round(similarity * 0.5, 4)
    return round(similarity * 0.8, 4)
