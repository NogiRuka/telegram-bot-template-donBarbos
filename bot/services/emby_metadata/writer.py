from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp

from bot.core.config import settings
from bot.services.emby_metadata.models import MetadataCandidate, MetadataNamedItem
from bot.services.emby_metadata.sources.ck_download import CkDownloadSource
from bot.utils.emby import get_emby_client

IMAGE_ARCHIVE_ROOT = Path("data/emby_metadata/images")

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
    "TagItems",
    "Taglines",
    "ProviderIds",
    "CommunityRating",
    "OfficialRating",
    "CustomRating",
)


def _named_items_to_payload(items: list[MetadataNamedItem]) -> list[dict[str, Any]]:
    return [item.model_dump(by_alias=False, exclude_none=True) | {"Name": item.name, **({"Id": item.id} if item.id else {})} for item in items]


def _person_to_payload(person: Any) -> dict[str, Any]:
    return person.model_dump(exclude_none=True, exclude={"image_url", "image_data", "image_path"})


def _image_headers(url: str, referer: str | None = None) -> dict[str, str]:
    parsed = urlparse(url)
    return {
        "Referer": referer or f"{parsed.scheme}://{parsed.netloc}/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }


def _archive_path(candidate: MetadataCandidate, filename: str) -> Path:
    safe_source = _safe_archive_component(candidate.source)
    safe_source_id = _safe_archive_component(candidate.source_id)
    return IMAGE_ARCHIVE_ROOT / safe_source / safe_source_id / _safe_archive_component(filename)


def _safe_archive_component(value: str) -> str:
    """把数据源标识转换为 Windows 和 Linux 都可用的目录名。"""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    return cleaned or "unknown"


def _should_verify_image_ssl(url: str) -> bool:
    """判断图片下载是否使用系统证书校验。"""
    url_lower = url.lower()
    return not any(
        host in url_lower
        for host in ("ko-shop.com", "ko-video.com", "ko-tube.com")
    )


async def _download_image_as_base64(
    url: str,
    *,
    referer: str | None = None,
    archive_path: Path | None = None,
    extra_headers: dict[str, str] | None = None,
) -> str:
    image_bytes, _ = await download_image(
        url,
        referer=referer,
        extra_headers=extra_headers,
        verify_ssl=_should_verify_image_ssl(url),
    )
    if archive_path is not None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(image_bytes)
    return base64.b64encode(image_bytes).decode("ascii")


async def download_image(
    url: str,
    *,
    referer: str | None = None,
    extra_headers: dict[str, str] | None = None,
    verify_ssl: bool = True,
) -> tuple[bytes, str]:
    """下载受防盗链保护的远程图片，供预览代理与写入流程共用。"""
    timeout = aiohttp.ClientTimeout(total=15)
    headers = _image_headers(url, referer)
    if extra_headers:
        headers.update(extra_headers)
    connector = aiohttp.TCPConnector(ssl=verify_ssl)
    async with aiohttp.ClientSession(timeout=timeout, headers=headers, connector=connector) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.read(), response.content_type


def _read_local_image_as_base64(path: str, *, archive_path: Path | None = None) -> str:
    image_bytes = Path(path).read_bytes()
    if archive_path is not None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(image_bytes)
    return base64.b64encode(image_bytes).decode("ascii")


def build_item_update_payload(
    item: dict[str, Any],
    candidate: MetadataCandidate,
    *,
    fields: set[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
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
    payload["People"] = [_person_to_payload(person) for person in candidate.people]
    payload["TagItems"] = _named_items_to_payload(candidate.tags)
    payload["Taglines"] = candidate.taglines
    payload["ProviderIds"] = dict(candidate.external_ids)
    payload["CommunityRating"] = candidate.community_rating
    payload["OfficialRating"] = candidate.official_rating
    payload["CustomRating"] = candidate.custom_rating
    field_mapping = {
        "Tags": "TagItems",
        "ExternalIds": "ProviderIds",
    }
    selected_fields = {field_mapping.get(field, field) for field in fields} if fields else None
    for field in ITEM_UPDATE_DIFF_FIELDS:
        if selected_fields is not None and field not in selected_fields:
            payload[field] = item.get(field)
        elif not overwrite and item.get(field) not in (None, "", [], {}):
            payload[field] = item[field]
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
    fields: set[str] | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """生成元数据更新预览。"""
    resolved_user_id, before_item = await fetch_item_snapshot(item_id, user_id=user_id)
    payload = build_item_update_payload(before_item, candidate, fields=fields, overwrite=overwrite)
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
    poster_url: str | None = None,
    poster_referer: str | None = None,
    poster_archive_path: Path | None = None,
    poster_headers: dict[str, str] | None = None,
    people: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """把载荷和图片写回指定 Emby Item。"""
    client = get_emby_client()
    if client is None:
        raise RuntimeError("Emby 客户端未配置")

    await client.update_item(item_id, payload)

    if apply_poster:
        image_data = poster_data
        if image_data is None and poster_url:
            image_data = await _download_image_as_base64(
                poster_url,
                referer=poster_referer,
                archive_path=poster_archive_path,
                extra_headers=poster_headers,
            )
        if image_data:
            await client.upload_item_image(item_id, image_data, "Primary")

    for person in people or []:
        person_id = person.get("Id")
        image_url = person.get("ImageUrl")
        image_data = person.get("ImageData")
        image_path = person.get("ImagePath")
        archive_path = person.get("ArchivePath")
        if not person_id:
            continue
        if image_data is None and image_path:
            image_data = _read_local_image_as_base64(image_path, archive_path=archive_path)
        if image_data is None and image_url:
            image_data = await _download_image_as_base64(
                image_url,
                referer=person.get("ImageReferer"),
                archive_path=archive_path,
            )
        if image_data:
            await client.upload_item_image(str(person_id), image_data, "Primary")

    return payload


async def apply_metadata_candidate_to_item(
    item_id: str,
    candidate: MetadataCandidate,
    *,
    user_id: str | None = None,
    fields: set[str] | None = None,
    overwrite: bool = False,
    apply_poster: bool = False,
    poster_data: str | None = None,
) -> dict[str, Any] | None:
    """执行元数据更新并返回更新前后对比。"""
    preview = await preview_metadata_candidate_update(
        item_id,
        candidate,
        user_id=user_id,
        fields=fields,
        overwrite=overwrite,
    )

    await apply_item_update(
        item_id,
        preview["payload"],
        apply_poster=apply_poster or bool(candidate.poster_url or candidate.poster_data),
        poster_data=poster_data or candidate.poster_data,
        poster_url=candidate.poster_url,
        poster_referer=candidate.raw_url,
        poster_archive_path=_archive_path(candidate, "poster.jpg"),
        poster_headers=(
            CkDownloadSource().image_headers(candidate.raw_url)
            if candidate.source == "ck-download"
            else None
        ),
        people=[],
    )

    _, after_item = await fetch_item_snapshot(item_id, user_id=preview["resolved_user_id"])

    people_by_name = {
        person.name: person
        for person in candidate.people
        if person.image_url or person.image_data or person.image_path
    }
    person_uploads = []
    for after_person in after_item.get("People", []):
        if not isinstance(after_person, dict):
            continue
        name = after_person.get("Name")
        person_id = after_person.get("Id")
        source_person = people_by_name.get(name)
        if not name or not person_id or source_person is None:
            continue
        person_uploads.append(
            {
                "Id": person_id,
                "ImageUrl": source_person.image_url,
                "ImageData": source_person.image_data,
                "ImagePath": source_person.image_path,
                "ImageReferer": candidate.raw_url,
                "ArchivePath": _archive_path(candidate, f"person_{name}.jpg"),
            }
        )

    if person_uploads:
        await apply_item_update(
            item_id,
            after_item,
            people=person_uploads,
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
