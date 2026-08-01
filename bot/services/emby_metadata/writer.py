from __future__ import annotations

from typing import Any

from bot.services.emby_metadata.models import MetadataCandidate
from bot.utils.emby import get_emby_client


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
    payload["Genres"] = list(candidate.genres)
    payload["Studios"] = list(candidate.studios)
    payload["People"] = [person.model_dump(exclude_none=True) for person in candidate.people]
    payload["ProviderIds"] = dict(candidate.external_ids)
    return payload


async def apply_item_update(
    item_id: str,
    payload: dict[str, Any],
    *,
    apply_poster: bool = False,
    poster_data: str | None = None,
) -> dict[str, Any] | None:
    """把载荷写回指定 Emby Item。"""
    client = get_emby_client()
    if client is None:
        return None

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
    """读取原 Item、合成载荷并写回指定 Emby Item。"""
    client = get_emby_client()
    if client is None:
        return None

    item = await client.get_item(user_id, item_id) if user_id else {"Id": item_id}
    payload = build_item_update_payload(item or {"Id": item_id}, candidate)
    return await apply_item_update(
        item_id,
        payload,
        apply_poster=apply_poster,
        poster_data=poster_data,
    )
