import argparse
import asyncio
import json

from bot.services.emby_metadata.models import MetadataCandidate, MetadataSearchResult
from bot.services.emby_metadata.sources.ck_download import CkDownloadSource


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查 Emby 元数据搜索结果")
    parser.add_argument("keyword", help="搜索关键词，例如 CO-LV00070")
    parser.add_argument("--limit", type=int, default=10, help="最多展示的搜索结果数量")
    parser.add_argument("--detail", help="选中的商品 ID，传入后才抓取详情")
    return parser.parse_args()


def _print_search_result(index: int, result: MetadataSearchResult) -> None:
    print(f"\n===== 搜索结果 {index} =====")
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def _print_detail(candidate: MetadataCandidate) -> None:
    print("\n===== 详情数据 =====")
    print(json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False, indent=2))


async def _inspect(keyword: str, limit: int, source_id: str | None) -> None:
    source = CkDownloadSource()
    results = await source.search(keyword, limit=limit)
    print(f"关键词: {keyword}")
    print(f"搜索结果数量: {len(results)}")
    if len(results) == 1:
        print("结果状态: 唯一结果，可以使用 --detail 抓取详情。")
    elif not results:
        print("结果状态: 没有搜索结果。")
    else:
        print("结果状态: 多个结果，请根据基础信息选择 source_id。")

    for index, result in enumerate(results, start=1):
        _print_search_result(index, result)

    if source_id is not None:
        selected = next((result for result in results if result.source_id == source_id), None)
        if selected is None:
            raise ValueError(f"搜索结果中不存在 source_id: {source_id}")
        _print_detail(await source.fetch_detail(selected.source_id))


def main() -> None:
    args = _parse_args()
    asyncio.run(_inspect(args.keyword, args.limit, args.detail))


if __name__ == "__main__":
    main()
