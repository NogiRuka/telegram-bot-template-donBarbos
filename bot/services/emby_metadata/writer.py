from __future__ import annotations

import copy
from typing import Any

from bot.core.config import settings
from bot.services.emby_metadata.models import MetadataCandidate
from bot.utils.emby import get_emby_client


async def apply_metadata_candidate_to_item(
    item_id: str,
    candidate: MetadataCandidate,
    *,
    user_id: str | None = None,
    apply_poster: bool = False,
    poster_data: str | None = None,
) -> dict[str, Any] | None:
    """把抓取到的元数据写回指定 Emby Item。"""
    client = get_emby_client()
    if client is None:
        return None

    target_user_id = user_id or settings.get_emby_template_user_id()
    item = await client.get_item(target_user_id, item_id) if target_user_id else {}
    if not item:
        item = {"Id": item_id}

    payload = copy.deepcopy(item)
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

    await client.update_item(item_id, payload)

    if apply_poster and poster_data:
        await client.upload_item_image(item_id, poster_data, "Primary")

    return payload
