from __future__ import annotations

from typing import Any

from bot.core.config import settings
from bot.services.emby_metadata.models import MetadataCandidate, MetadataNamedItem
from bot.utils.emby import get_emby_client

ITEM_UPDATE_DIFF_FIELDS = (
    "Name",
    "OriginalTitle",
    "SortName",
    "ForcedSortName",
    "Overview",
    "ProductionYear",
    "PremiereDate",
    "Genres",
    "Studios",
    "People",
    "ProviderIds",
)


def _named_items_to_payload(items: list[MetadataNamedItem]) -> list[dict[str, Any]]:
    return [item.model_dump(by_alias=False, exclude_none=True) | {"Name": item.name, **({"Id": item.id} if item.id else {})} for item in items]


def build_item_update_payload(item: dict[str, Any], candidate: MetadataCandidate) -> dict[str, Any]:
    """根据候选元数据构建 Emby Item 更新载荷。"""
    payload = dict(item)
    payload["Name"] = candidate.title
    payload["OriginalTitle"] = candidate.original_title
    payload["SortName"] = candidate.sort_name
    payload["ForcedSortName"] = candidate.forced_sort_name
    payload["Overview"] = candidate.overview
    payload["ProductionYear"] = candidate.year
    payload["PremiereDate"] = candidate.release_date.isoformat() if candidate.release_date else None
    payload["Genres"] = [genre.name for genre in candidate.genres]
    payload["GenreItems"] = _named_items_to_payload(candidate.genres)
    payload["Studios"] = _named_items_to_payload(candidate.studios)
    payload["People"] = [person.model_dump(exclude_none=True) for person in candidate.people]
    payload["TagItems"] = _named_items_to_payload(candidate.tags)
    payload["Taglines"] = candidate.taglines
    payload["ProviderIds"] = dict(candidate.external_ids)
    return payload


def build_item_update_changes(
    before_item: dict[str, Any],
    after_item: dict[str, Any],
    *,
    fields: tuple[str, ...] | None = ITEM_UPDATE_DIFF_FIELDS,
) -> list[dict[str, Any]]:
    """构建 Item 字段前后差异。"""
    changes: list[dict[str, Any]] = []
    compare_fields = fields or tuple(sorted(set(before_item) | set(after_item)))
    for field in compare_fields:
        before_value = before_item.get(field)
        after_value = after_item.get(field)
        if before_value != after_value:
            changes.append({"field": field, "before": before_value, "after": after_value})
    return changes


def extract_unexpected_item_changes(
    requested_changes: list[dict[str, Any]],
    actual_changes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """提取未计划但实际发生的字段变化。"""
    requested_fields = {change["field"] for change in requested_changes}
    return [change for change in actual_changes if change["field"] not in requested_fields]


async def fetch_item_snapshot(item_id: str, *, user_id: str | None = None) -> tuple[str | None, dict[str, Any]]:
    """读取 Item 快照，默认使用模板用户。"""
    client = get_emby_client()
    resolved_user_id = user_id or settings.get_emby_template_user_id()
    if not resolved_user_id:
        return None, {"Id": item_id}
    item = await client.get_item(resolved_user_id, item_id)
    return resolved_user_id, item or {"Id": item_id}


async def preview_metadata_candidate_update(
    item_id: str,
    candidate: MetadataCandidate,
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """生成元数据更新预览。"""
    resolved_user_id, before_item = await fetch_item_snapshot(item_id, user_id=user_id)
    payload = build_item_update_payload(before_item, candidate)
    planned_core_changes = build_item_update_changes(before_item, payload)
    planned_changes = build_item_update_changes(before_item, payload, fields=None)
    return {
        "item_id": item_id,
        "resolved_user_id": resolved_user_id,
        "before_item": before_item,
        "payload": payload,
        "planned_core_changes": planned_core_changes,
        "planned_changes": planned_changes,
    }


async def apply_item_update(
    item_id: str,
    payload: dict[str, Any],
    *,
    apply_poster: bool = False,
    poster_data: str | None = None,
) -> dict[str, Any] | None:
    """把载荷写回指定 Emby Item。"""
    client = get_emby_client()

    await client.update_item(item_id, payload)

    if apply_poster and poster_data:
        await client.upload_item_image(item_id, poster_data, "Primary")

    return payload


async def apply_metadata_candidate_to_item(
    item_id: str,
    candidate: MetadataCandidate,
    *,
    user_id: str | None = None,
    apply_poster: bool = False,
    poster_data: str | None = None,
) -> dict[str, Any] | None:
    """执行元数据更新并返回更新前后对比。"""
    preview = await preview_metadata_candidate_update(item_id, candidate, user_id=user_id)

    await apply_item_update(
        item_id,
        preview["payload"],
        apply_poster=apply_poster,
        poster_data=poster_data,
    )

    _, after_item = await fetch_item_snapshot(item_id, user_id=preview["resolved_user_id"])
    actual_core_changes = build_item_update_changes(preview["before_item"], after_item)
    actual_changes = build_item_update_changes(preview["before_item"], after_item, fields=None)
    writeback_diffs = build_item_update_changes(preview["payload"], after_item, fields=None)

    preview["after_item"] = after_item
    preview["actual_core_changes"] = actual_core_changes
    preview["actual_changes"] = actual_changes
    preview["writeback_diffs"] = writeback_diffs
    preview["unexpected_changes"] = extract_unexpected_item_changes(
        preview["planned_changes"],
        actual_changes,
    )
    return preview
