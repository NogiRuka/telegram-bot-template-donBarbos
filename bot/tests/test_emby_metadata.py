import asyncio
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

from bot.services.emby_metadata.matching import (
    calculate_confidence,
    extract_product_number,
    normalize_product_number,
    normalize_search_keyword,
)
from bot.services.emby_metadata.models import (
    MediaLibraryCategory,
    MetadataCandidate,
    MetadataNamedItem,
    MetadataSearchResult,
)
from bot.services.emby_metadata.parser.acceed import AcceedParser
from bot.services.emby_metadata.parser.boy_studio import BoyStudioParser
from bot.services.emby_metadata.parser.ck_download import CkDownloadParser
from bot.services.emby_metadata.parser.hunk_ch import HunkChParser
from bot.services.emby_metadata.parser.ko_shop import KoShopParser
from bot.services.emby_metadata.parser.ko_tube import KoTubeParser
from bot.services.emby_metadata.parser.ko_video import KoVideoParser
from bot.services.emby_metadata.parser.mensrush import MensrushParser
from bot.services.emby_metadata.parser.trance_video import TranceVideoParser
from bot.services.emby_metadata.sources.acceed import AcceedSource
from bot.services.emby_metadata.sources.base import MetadataSourceParseError
from bot.services.emby_metadata.writer import (
    apply_metadata_candidate_to_item,
    build_item_update_changes,
    build_item_update_payload,
    extract_unexpected_item_changes,
    preview_metadata_candidate_update,
)

_FIXTURE_ROOT = Path(__file__).parents[1] / "services" / "emby_metadata" / "fixtures" / "ck_download"
_HUNK_FIXTURE_ROOT = Path(__file__).parents[1] / "services" / "emby_metadata" / "fixtures" / "hunk_ch"
_FIXTURE_SOURCE_ROOT = Path(__file__).parents[1] / "services" / "emby_metadata" / "fixtures" / "日韩"


class MatchingTests(unittest.TestCase):
    def test_extract_product_number(self) -> None:
        assert extract_product_number("CO-ME00059 标题") == "CO-ME00059"
        assert extract_product_number("CO-ME-00059 标题") == "CO-ME-00059"
        assert extract_product_number("No.059 标题") == "No.059"
        assert extract_product_number("2026 日本映画") is None

    def test_normalize_product_number(self) -> None:
        assert normalize_product_number("co me-00059") == "COME00059"

    def test_gv_prefix_is_removed_for_search_keyword(self) -> None:
        assert normalize_search_keyword("GV-OAV1350") == "OAV1350"

    def test_exact_product_number_has_highest_confidence(self) -> None:
        exact = calculate_confidence("CO-ME00059 标题", "Different title", "CO-ME-00059")
        mismatch = calculate_confidence("CO-ME00059 标题", "CO-ME00059 标题", "ABP-123")
        assert exact == 1.0
        assert exact > mismatch


class CkDownloadParserTests(unittest.TestCase):
    @staticmethod
    def _read_fixture(name: str) -> str:
        return (_FIXTURE_ROOT / name).read_text(encoding="utf-8")

    def test_parse_single_product_detail(self) -> None:
        candidate = CkDownloadParser.parse_detail(self._read_fixture("detail/33907.html"), "33907")
        assert candidate.category == MediaLibraryCategory.JAPANESE_KOREAN
        assert candidate.product_number == "CO-GF00023"
        assert candidate.title.startswith("CO-GF00023 ")
        assert candidate.title == candidate.sort_name
        assert candidate.title == candidate.forced_sort_name
        assert candidate.original_title == candidate.title.removeprefix("CO-GF00023 ")
        assert candidate.release_date == date(2026, 7, 21)
        assert candidate.year == 2026
        assert candidate.runtime_minutes == 26
        assert [studio.name for studio in candidate.studios] == ["CKオリジナル"]
        assert candidate.people == []
        assert candidate.poster_url == "https://img.ck-download.com/images/product/33907/33907_1.jpg"
        assert "フェラチオ" in [genre.name for genre in candidate.genres]
        assert "激撮フィッティングルーム" in [tag.name for tag in candidate.tags]
        assert "※この作品の視聴方法" not in (candidate.overview or "")
        assert "販売価格" not in (candidate.overview or "")

    def test_parse_set_product_detail(self) -> None:
        candidate = CkDownloadParser.parse_detail(self._read_fixture("detail/33831.html"), "33831")
        assert candidate.product_number == "COCO562"
        assert candidate.runtime_minutes == 126
        assert candidate.year == 2026
        assert [studio.name for studio in candidate.studios] == ["COAT"]
        assert [person.name for person in candidate.people] == ["聖哉", "夏葵", "大希(TAIKI)", "仁(JIN)＜東京＞"]
        assert candidate.poster_url == "https://img.ck-download.com/images/product/33831/33831_1.jpg"

    def test_parse_saved_search_results(self) -> None:
        results = CkDownloadParser.parse_search_results(self._read_fixture("search/COCO060.html"))
        assert len(results) == 5
        assert all(isinstance(result, MetadataSearchResult) for result in results)
        assert [result.source_id for result in results] == ["18996", "18997", "18998", "18999", "19000"]
        assert results[0].title == "[Hello!] 斗武と魁斗のオナホ品評会! 淫猥巨根にガン掘られ!!"
        assert results[0].release_date == date(2023, 8, 4)
        assert results[0].price_yen == 2074
        assert results[0].statuses == ["単品", "HD", "レンタル", "ブラウザ視聴専用"]
        assert results[0].image_urls == ["https://img.ck-download.com/images/product/18996/18996_1_360.jpg", "https://img.ck-download.com/images/product/18996/18996_2_360.jpg", "https://img.ck-download.com/images/product/18996/18996_3_360.jpg"]
        assert CkDownloadParser.parse_search_results(self._read_fixture("search/COCO060.html"), limit=1) == results[:1]

    def test_parse_search_results_deduplicates_and_supports_absolute_urls(self) -> None:
        html = """
        <div class="product_list">
            <a href="/product/detail/33907"><h5>First title</h5></a>
            <a href="https://www.ck-download.com/product/detail/33907"><h5>Duplicate title</h5></a>
            <a href="/product/detail/33831"><h5>Second title</h5></a>
        </div>
        """
        results = CkDownloadParser.parse_search_results(html)
        assert [(result.source_id, result.title) for result in results] == [("33907", "First title"), ("33831", "Second title")]
        assert [(result.source_id, result.title) for result in CkDownloadParser.parse_search_results(html, limit=1)] == [("33907", "First title")]

    def test_empty_search_results(self) -> None:
        assert CkDownloadParser.parse_search_results("<html></html>") == []
        assert CkDownloadParser.parse_search_results("<html></html>", limit=0) == []

    def test_missing_title_raises_parse_error(self) -> None:
        with pytest.raises(MetadataSourceParseError):
            CkDownloadParser.parse_detail("<html><table></table></html>", "33907")

    def test_invalid_source_id_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            CkDownloadParser.parse_detail("<html></html>", "../33907")


class HunkChParserTests(unittest.TestCase):
    @staticmethod
    def _read_fixture(name: str) -> str:
        return (_HUNK_FIXTURE_ROOT / name).read_text(encoding="utf-8")

    def test_parse_search_results(self) -> None:
        results = HunkChParser.parse_search_results(self._read_fixture("search/OAV135.html"))
        assert [result.source_id for result in results] == ["GV-OAV1350", "GV-OAV135_DL"]
        assert results[0].release_date == date(2026, 8, 4)
        assert results[0].price_yen == 1080
        assert results[0].image_urls[0].endswith("gv-oav1350_pickup01.jpg")

    def test_parse_detail(self) -> None:
        candidate = HunkChParser.parse_detail(
            self._read_fixture("detail/GV-OAV1350.html"), "GV-OAV1350"
        )
        assert candidate.category == MediaLibraryCategory.JAPANESE_KOREAN
        assert candidate.product_number == "OAV1350"
        assert candidate.genres == []
        assert candidate.release_date == date(2026, 8, 4)
        assert [studio.name for studio in candidate.studios] == ["マラ面接!!"]
        assert candidate.poster_url.endswith("gv-oav1350_top.jpg")
        assert candidate.overview


class MensrushParserTests(unittest.TestCase):
    def test_search_result_uses_primary_product_card(self) -> None:
        html = (
            _FIXTURE_SOURCE_ROOT / "mensrush" / "search" / "GT-2715.html"
        ).read_text(encoding="utf-8")

        results = MensrushParser.parse_search_results(html)

        assert len(results) == 1
        assert results[0].source_id == "GT-2715_DL"
        assert results[0].title == "顔と同じぐらいの大きさがある巨根を挿入で即トコロテン！！"
        assert results[0].price_yen == 1850


class KoShopParserTests(unittest.TestCase):
    def test_series_is_not_added_to_tags(self) -> None:
        html = """
        <div class="detail_product">
            <h2>商品标题</h2>
            <dl>
                <dt>商品コード</dt><dd>ABC123_DVD</dd>
                <dt>発売日</dt><dd>2026年8月13日</dd>
                <dt>モデルタイプ</dt><dd>类型A / 类型B</dd>
                <dt>シリーズ</dt><dd>系列名</dd>
                <dt>キーワード</dt><dd><a href="/keyword/a">关键词A</a></dd>
            </dl>
        </div>
        """

        candidate = KoShopParser.parse_detail(html, "123")

        assert [tag.name for tag in candidate.tags] == ["类型A", "类型B", "系列名", "关键词A"]


class EmbyMetadataSourceParserTests(unittest.TestCase):
    @staticmethod
    def _fixture(source: str, kind: str, name: str) -> str:
        return (_FIXTURE_SOURCE_ROOT / source / kind / name).read_text(encoding="utf-8")

    def test_multi_word_labels_are_single_tags(self) -> None:
        ko_video = KoVideoParser.parse_detail(
            "<h2>标题</h2><dl><dt>メーカー/レーベル</dt><dd>KO/Secret Film</dd>"
            "<dt>シリーズ/ジャンル</dt><dd>ストーリー</dd></dl>",
            "KSUI028",
        )
        assert "Secret Film" in [tag.name for tag in ko_video.tags]

        ko_tube = KoTubeParser.parse_detail(
            "<h3>标题</h3><table class='movie_data'><tr><th>作品番号</th>"
            "<td>70-01-0035-01</td></tr><tr><th>レーベル</th>"
            "<td>TUBE オリジナル</td></tr></table>",
            "70-01-0035-01",
        )
        assert "TUBE オリジナル" in [tag.name for tag in ko_tube.tags]

    def test_trance_video_search_parses_statuses(self) -> None:
        results = TranceVideoParser.parse_search_results(
            self._fixture("trance-video", "search", "TO-07-0011-01.html")
        )
        assert results[0].statuses == ["オススメ", "単品"]


class AcceedParserTests(unittest.TestCase):
    @staticmethod
    def _read_fixture(name: str) -> str:
        fixture_root = next(path for path in _FIXTURE_ROOT.parent.rglob("acceed") if path.is_dir())
        return (fixture_root / name).read_text(encoding="utf-8")

    def test_search_result_image_urls_are_trimmed(self) -> None:
        results = AcceedParser.parse_search_results(self._read_fixture("search/ACSM355.html"))

        assert results
        assert results[0].image_urls
        assert results[0].image_urls[0] == results[0].image_urls[0].rstrip()
        assert results[0].image_urls[0].endswith("_pickup.jpg")

    def test_detail_title_excludes_favorite_link(self) -> None:
        candidate = AcceedParser.parse_detail(self._read_fixture("detail/ACSM355.html"), "ACSM355")

        assert candidate.original_title.startswith("ACCEED STAR 2024")
        assert "神山" in candidate.original_title
        assert "お気に入り" not in candidate.original_title

    def test_detail_rejects_login_page(self) -> None:
        with self.assertRaisesRegex(MetadataSourceParseError, "登录页"):
            AcceedParser.parse_detail("<title>ログイン</title><h2>ログイン</h2>", "ACSM355")

    def test_fetch_detail_prepares_a_shared_session(self) -> None:
        source = AcceedSource()
        detail_html = self._read_fixture("detail/ACSM355.html")
        source._request_text_sequence = AsyncMock(return_value=["<html></html>", detail_html])

        candidate = asyncio.run(source.fetch_detail("ACSM355"))

        assert candidate.original_title.startswith("ACCEED STAR 2024")
        source._request_text_sequence.assert_awaited_once_with(
            ("/search.php?s=ACSM355", "/detail.ACSM355.html")
        )


class BoyStudioParserTests(unittest.TestCase):
    @staticmethod
    def _fixture(name: str) -> str:
        root = next(path for path in _FIXTURE_ROOT.parent.rglob("boy-studio") if path.is_dir())
        return (root / name).read_text(encoding="utf-8")

    def test_parse_search_results(self) -> None:
        results = BoyStudioParser.parse_search_results(self._fixture("search/今どきヒゲイケメン、シコシコ開始。.html"))

        assert len(results) == 1
        assert results[0].source_id == "4748"
        assert results[0].title == "今どきヒゲイケメン、シコシコ開始。"
        assert results[0].image_urls[0].endswith(".webp")

    def test_parse_detail(self) -> None:
        candidate = BoyStudioParser.parse_detail(self._fixture("detail/BOY-671.html"), "4748")

        assert candidate.product_number == "BOY-671"
        assert candidate.title == "BOY-671 今どきヒゲイケメン、シコシコ開始。"
        assert candidate.release_date == date(2026, 5, 15)
        assert candidate.poster_url.endswith(".webp")
        assert "オナニー" in [tag.name for tag in candidate.tags]


class WriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidate = MetadataCandidate(
            source="ck_download",
            source_id="33907",
            category=MediaLibraryCategory.JAPANESE_KOREAN,
            product_number="CO-GF00023",
            title="CO-GF00023 标题A",
            original_title="标题A",
            sort_name="CO-GF00023 标题A",
            forced_sort_name="CO-GF00023 标题A",
            overview="新的简介",
            year=2026,
            release_date=date(2026, 7, 21),
            genres=[MetadataNamedItem(name="A"), MetadataNamedItem(name="B")],
            studios=[MetadataNamedItem(name="StudioA")],
            people=[],
            tags=[],
            external_ids={"imdb": "tt123"},
            poster_url=None,
            runtime_minutes=26,
            confidence=1.0,
            raw_url="https://example.com/detail/33907",
        )
        self.before_item = {
            "Id": "item-1",
            "Name": "旧标题",
            "OriginalTitle": "旧标题",
            "SortName": "旧标题",
            "ForcedSortName": "旧标题",
            "Overview": "旧简介",
            "ProductionYear": 2025,
            "PremiereDate": "2025-01-01",
            "Genres": ["Old"],
            "Studios": ["OldStudio"],
            "People": [],
            "ProviderIds": {"tmdb": "1"},
        }

    def test_build_item_update_payload(self) -> None:
        payload = build_item_update_payload(self.before_item, self.candidate)
        assert payload["Name"] == "CO-GF00023 标题A"
        assert payload["Overview"] == "新的简介"
        assert payload["Genres"] == ["A", "B"]
        assert payload["ProviderIds"] == {"imdb": "tt123"}

    def test_build_item_update_payload_wraps_tagline_for_emby(self) -> None:
        candidate = self.candidate.model_copy(
            update={"taglines": "【HUNK原创：Full HD】完整宣传语"}
        )

        payload = build_item_update_payload(self.before_item, candidate)

        assert payload["Taglines"] == ["【HUNK原创：Full HD】完整宣传语"]

    def test_build_item_update_changes_with_core_fields(self) -> None:
        payload = build_item_update_payload(self.before_item, self.candidate)
        changes = build_item_update_changes(self.before_item, payload)
        fields = [change["field"] for change in changes]
        assert "Name" in fields
        assert "Overview" in fields
        assert "Id" not in fields

    def test_build_item_update_changes_full_scan_detects_extra_fields(self) -> None:
        after_item = dict(self.before_item)
        after_item["UnexpectedField"] = "changed"
        changes = build_item_update_changes(self.before_item, after_item, fields=None)
        assert changes == [{"field": "UnexpectedField", "before": None, "after": "changed"}]

    def test_extract_unexpected_item_changes(self) -> None:
        requested_changes = [{"field": "Name", "before": "旧标题", "after": "新标题"}]
        actual_changes = [
            {"field": "Name", "before": "旧标题", "after": "新标题"},
            {"field": "Genres", "before": ["Old"], "after": ["A", "B"]},
        ]
        unexpected = extract_unexpected_item_changes(requested_changes, actual_changes)
        assert unexpected == [{"field": "Genres", "before": ["Old"], "after": ["A", "B"]}]

    @patch("bot.services.emby_metadata.writer.fetch_item_snapshot", new_callable=AsyncMock)
    def test_preview_metadata_candidate_update_uses_template_user(self, mock_fetch: AsyncMock) -> None:
        mock_fetch.return_value = ("template-user", self.before_item)

        result = asyncio.run(preview_metadata_candidate_update("item-1", self.candidate))
        assert result["resolved_user_id"] == "template-user"
        assert result["before_item"]["Name"] == "旧标题"
        assert result["planned_changes"]

    @patch("bot.services.emby_metadata.writer.fetch_item_snapshot", new_callable=AsyncMock)
    @patch("bot.services.emby_metadata.writer.apply_item_update", new_callable=AsyncMock)
    def test_apply_metadata_candidate_to_item_returns_writeback_diffs(self, mock_apply: AsyncMock, mock_fetch: AsyncMock) -> None:
        mock_fetch.side_effect = [
            ("template-user", self.before_item),
            ("template-user", {**self.before_item, "Name": "CO-GF00023 标题A", "Genres": ["A", "B"]}),
        ]
        mock_apply.return_value = build_item_update_payload(self.before_item, self.candidate)

        result = asyncio.run(apply_metadata_candidate_to_item("item-1", self.candidate))
        assert result["resolved_user_id"] == "template-user"
        assert "after_item" in result
        assert result["actual_changes"]
        assert result["writeback_diffs"]


if __name__ == "__main__":
    unittest.main()
