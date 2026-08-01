import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate
from bot.services.emby_metadata.writer import apply_metadata_candidate_to_item, preview_metadata_candidate_update


def build_candidate() -> MetadataCandidate:
    candidate = MetadataCandidate(
        source="ck_download",
        source_id="18996",
        category=MediaLibraryCategory.JAPANESE_KOREAN,
        product_number="COCO060-04",
        title="COCO060-04 [Hello!] 斗武と魁斗のオナホ品評会! 淫猥巨根にガン掘られ!!",
        original_title="[Hello!] 斗武と魁斗のオナホ品評会! 淫猥巨根にガン掘られ!!",
        sort_name="COCO060-04 [Hello!] 斗武と魁斗のオナホ品評会! 淫猥巨根にガン掘られ!!",
        forced_sort_name="COCO060-04 [Hello!] 斗武と魁斗のオナホ品評会! 淫猥巨根にガン掘られ!!",
        overview="""※この作品の視聴方法はストリーミング再生のみとなります。動画データを端末に保存すること（ダウンロード再生）はできませんので予めご了承願います。

魁斗20才とオナホ―ル品評会! 淫猥巨根にガン掘られ!!
バドミントン対決! 斗武が空中逆上がり披露!
変わり種オナホで扱き合って体験レポ! 斗武のデカチンがオナホを突き破り…!
オナホとフェラのどちらが気持ちいいのか検証! 「オナホみたいに魁斗さんの喉も破っていい?」 頭を掴んでイラマチオ! 魁斗も斗武にやり返し…!
バックの体勢で斗武の股に挟ませたオナホにピストンする魁斗! 「上の穴とどっちが気持ちいいか比べてみるね」
巨根をぶち込まれた衝撃に顔を歪める斗武! 「さっきのオナホとどっちが気持ちいい?」「そりゃあ、もちろんこっちでしょ!」
真っ白なプリケツを揉まれ叩かれ…ボリュームのあるスッポリ仮性包茎も弄られて…!
「ちょっとおっきくなってきたんじゃない?」「うん…」 斗武、掘られイキ&顔射!!""",
        year=2023,
        release_date=None,
        genres=["フェラチオ", "イラマチオ", "巨根", "オナホール"],
        studios=["Hello!"],
        people=[
            {"name": "魁斗", "role": None, "type": "Actor"},
            {"name": "斗武", "role": None, "type": "Actor"},
        ],
        labels=["COCO060", "Hello!", "HD"],
        external_ids={
            "source": "ck_download",
            "source_id": "18996",
            "product_number": "COCO060-04",
        },
        poster_url="https://img.ck-download.com/images/product/18996/18996_1_360.jpg",
        runtime_minutes=None,
        confidence=1.0,
        raw_url="https://www.ck-download.com/product/detail/18996", 
    )

    return candidate


async def run_preview() -> None:
    candidate = build_candidate()
    result = await preview_metadata_candidate_update("26222", candidate)
    before_item = result["before_item"]
    payload = result["payload"]
    print("mode: preview")
    print("resolved_user_id:", result["resolved_user_id"])
    print("before Name:", before_item.get("Name"))
    print("payload Name:", payload.get("Name"))
    print("before Overview:", (before_item.get("Overview") or "")[:200])
    print("payload Overview:", (payload.get("Overview") or "")[:200])
    print("planned_changes:", result["planned_changes"])
    print("unexpected_changes:", result.get("unexpected_changes", []))


async def run_apply() -> None:
    candidate = build_candidate()
    result = await apply_metadata_candidate_to_item("26222", candidate)
    before_item = result["before_item"]
    after_item = result["after_item"]
    print("mode: apply")
    print("resolved_user_id:", result["resolved_user_id"])
    print("before Name:", before_item.get("Name"))
    print("after Name:", after_item.get("Name"))
    print("before Overview:", (before_item.get("Overview") or "")[:200])
    print("after Overview:", (after_item.get("Overview") or "")[:200])
    print("actual_changes:", result["actual_changes"])
    print("writeback_diffs:", result["writeback_diffs"])
    print("unexpected_changes:", result.get("unexpected_changes", []))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="实际写回 Emby")
    args = parser.parse_args()
    asyncio.run(run_apply() if args.apply else run_preview())


if __name__ == "__main__":
    main()