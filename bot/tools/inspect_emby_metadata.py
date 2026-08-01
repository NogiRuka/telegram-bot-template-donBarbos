import argparse
import asyncio
import json

from bot.services.emby_metadata.models import MetadataCandidate
from bot.services.emby_metadata.sources.ck_download import CkDownloadSource


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 Emby 元数据候选结果")
    parser.add_argument("keyword", help="搜索关键词，例如 CO-LV00070")
    parser.add_argument("--limit", type=int, default=10, help="最多获取的候选数量")
    return parser.parse_args()


def _print_candidate(index: int, candidate: MetadataCandidate) -> None:
    print(f"\n===== 候选 {index} =====")
    print(json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False, indent=2))


async def _inspect(keyword: str, limit: int) -> None:
    candidates = await CkDownloadSource().search(keyword, limit=limit)
    print(f"关键词: {keyword}")
    print(f"候选数量: {len(candidates)}")
    if len(candidates) == 1:
        print("结果状态: 唯一匹配，请核对下面的元数据。")
    elif not candidates:
        print("结果状态: 没有搜索结果。")
    else:
        print("结果状态: 多个候选，请按置信度和字段内容人工选择。")

    for index, candidate in enumerate(candidates, start=1):
        _print_candidate(index, candidate)


def main() -> None:
    args = _parse_args()
    asyncio.run(_inspect(args.keyword, args.limit))


if __name__ == "__main__":
    main()
