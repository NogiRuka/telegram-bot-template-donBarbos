import unittest
from datetime import date

from bot.services.emby_metadata.matching import (
    calculate_confidence,
    extract_product_number,
    normalize_product_number,
)
from bot.services.emby_metadata.models import MediaLibraryCategory
from bot.services.emby_metadata.sources.base import MetadataSourceParseError
from bot.services.emby_metadata.sources.ck_download import CkDownloadSource

DETAIL_HTML = """
<html><body>
  <main>
    <h3>[メンズエロマ]No.059 Sample Title</h3>
    <div class="published">2026.07.28 UP</div>
    <p>First introduction paragraph.</p>
    <p>Second introduction paragraph.</p>
    <div>販売価格 2,180 円（税込）</div>
    <div><strong>プレイ内容</strong><a href="/product/search?p[]=116">手コキ</a><a>マッサージ</a></div>
    <div><strong>モデルタイプ</strong><a href="/product/search?mt[]=1">スリム</a></div>
    <h4>商品情報</h4>
    <table>
      <tr><th>プロダクトナンバー</th><td>CO-ME00059</td><th>ファイルサイズ</th><td>stream</td></tr>
      <tr><th>再生時間</th><td>0:26:30</td><th>メーカー</th><td><a>CKオリジナル</a></td></tr>
      <tr><th>レーベル</th><td><a>メンズエロマ</a></td><th>DVD発売年</th><td>2025</td></tr>
      <tr><th>DVDタイトル</th><td>Original DVD Title</td></tr>
    </table>
    <img src="/images/banner.jpg">
  </main>
</body></html>
"""


class MatchingTests(unittest.TestCase):
    def test_extract_compact_product_number(self) -> None:
        self.assertEqual(extract_product_number("CO-ME00059 标题"), "CO-ME00059")

    def test_extract_extra_hyphen_product_number(self) -> None:
        self.assertEqual(extract_product_number("CO-ME-00059 标题"), "CO-ME-00059")

    def test_extract_standard_product_number(self) -> None:
        self.assertEqual(extract_product_number("ABP-123 标题"), "ABP-123")

    def test_extract_number_prefix(self) -> None:
        self.assertEqual(extract_product_number("No.059 标题"), "No.059")

    def test_does_not_extract_plain_year(self) -> None:
        self.assertIsNone(extract_product_number("2026 日本映画"))

    def test_does_not_extract_japanese_title(self) -> None:
        self.assertIsNone(extract_product_number("疲れた心身に安らぎのひと時を"))

    def test_normalize_ignores_case_hyphen_and_spaces(self) -> None:
        self.assertEqual(normalize_product_number("co me-00059"), "COME00059")

    def test_exact_product_number_has_highest_confidence(self) -> None:
        exact = calculate_confidence("CO-ME00059 标题", "Different title", "CO-ME-00059")
        mismatch = calculate_confidence("CO-ME00059 标题", "CO-ME00059 标题", "ABP-123")
        self.assertGreater(exact, mismatch)
        self.assertGreaterEqual(exact, 0.9)


class CkDownloadParserTests(unittest.TestCase):
    def test_parse_detail_fields(self) -> None:
        candidate = CkDownloadSource.parse_detail(DETAIL_HTML, "33968")
        self.assertEqual(candidate.source, "ck_download")
        self.assertEqual(candidate.category, MediaLibraryCategory.JAPANESE_KOREAN)
        self.assertEqual(candidate.external_ids, {"CkDownload": "CO-ME00059"})
        self.assertEqual(candidate.release_date, date(2026, 7, 28))
        self.assertEqual(candidate.year, 2026)
        self.assertEqual(candidate.runtime_minutes, 27)
        self.assertEqual(candidate.studios, ["CKオリジナル"])
        self.assertEqual(candidate.genres, ["手コキ", "マッサージ"])
        self.assertEqual(candidate.labels, ["メンズエロマ", "スリム", "手コキ", "マッサージ"])
        self.assertEqual(candidate.original_title, "Original DVD Title")
        self.assertEqual(candidate.overview, "First introduction paragraph.\nSecond introduction paragraph.")
        self.assertIsNone(candidate.poster_url)

    def test_search_results_are_deduplicated(self) -> None:
        html = """
        <a href="/product/detail/33968">First title</a>
        <a href="https://ck-download.com/product/detail/33968">Duplicate title</a>
        <a href="/product/detail/12345">Second title</a>
        """
        self.assertEqual(
            CkDownloadSource.parse_search_results(html),
            [("33968", "First title"), ("12345", "Second title")],
        )

    def test_search_result_limit(self) -> None:
        html = '<a href="/product/detail/1">One</a><a href="/product/detail/2">Two</a>'
        self.assertEqual(CkDownloadSource.parse_search_results(html, limit=1), [("1", "One")])

    def test_missing_title_raises_parse_error(self) -> None:
        with self.assertRaises(MetadataSourceParseError):
            CkDownloadSource.parse_detail("<html><table></table></html>", "33968")

    def test_invalid_source_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CkDownloadSource.parse_detail(DETAIL_HTML, "../33968")

    def test_explicit_product_image_is_accepted(self) -> None:
        html = DETAIL_HTML.replace(
            '<img src="/images/banner.jpg">',
            '<div class="product-image"><img src="/media/cover.jpg"></div>',
        )
        candidate = CkDownloadSource.parse_detail(html, "33968")
        self.assertEqual(candidate.poster_url, "https://ck-download.com/media/cover.jpg")


if __name__ == "__main__":
    unittest.main()
