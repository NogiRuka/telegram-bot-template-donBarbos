"""Emby 元数据工作台的队列查询、候选搜索和写入编排。"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote, urlencode

from fastapi import HTTPException
from sqlalchemy import select

from bot.core.config import settings
from bot.database.database import sessionmaker
from bot.database.models import LibraryNewNotificationModel
from bot.services.emby_metadata.models import MediaLibraryCategory, MetadataCandidate
from bot.services.emby_metadata.matching import extract_product_number, is_hunk_ch_product_number, normalize_search_keyword
from bot.services.emby_metadata.sources.ck_download import CkDownloadSource
from bot.services.emby_metadata.sources.acceed import AcceedSource
from bot.services.emby_metadata.sources.boy_studio import BoyStudioSource
from bot.services.emby_metadata.sources.hunk_ch import HunkChSource
from bot.services.emby_metadata.sources.jgvdata import JgvdataSource
from bot.services.emby_metadata.sources.ko_shop import KoShopSource
from bot.services.emby_metadata.sources.mensrush import MensrushSource
from bot.services.emby_metadata.sources.base import MetadataSource
from bot.services.emby_metadata.writer import (
    apply_metadata_candidate_to_item,
    download_image,
    preview_metadata_candidate_update,
    fetch_item_snapshot,
)


_search_cache: dict[str, list[dict[str, Any]]] = {}


def _merge_named_items(primary: list[Any], supplement: list[Any]) -> list[Any]:
    merged = list(primary)
    seen = {str(item.name).strip().casefold() for item in merged if getattr(item, "name", "").strip()}
    for item in supplement:
        name = str(getattr(item, "name", "")).strip()
        if name and name.casefold() not in seen:
            merged.append(item)
            seen.add(name.casefold())
    return merged


def _merge_people(primary: list[Any], supplement: list[Any]) -> list[Any]:
    merged = list(primary)
    seen = {person.name.strip().casefold() for person in merged if person.name.strip()}
    for person in supplement:
        name = person.name.strip()
        if name and name.casefold() not in seen:
            merged.append(person)
            seen.add(name.casefold())
    return merged


def merge_metadata_candidates(primary: MetadataCandidate, supplement: MetadataCandidate) -> MetadataCandidate:
    """以主来源为准合并补充来源，避免 CK 覆盖 Koshop 的标题和番号。"""
    external_ids = dict(primary.external_ids)
    external_ids.update({f"{supplement.source}_{key}": value for key, value in supplement.external_ids.items()})
    return primary.model_copy(update={
        "overview": primary.overview or supplement.overview,
        "year": primary.year or supplement.year,
        "release_date": primary.release_date or supplement.release_date,
        "genres": _merge_named_items(primary.genres, supplement.genres),
        "studios": _merge_named_items(primary.studios, supplement.studios),
        "people": _merge_people(primary.people, supplement.people),
        "tags": _merge_named_items(primary.tags, supplement.tags),
        "taglines": primary.taglines or supplement.taglines,
        "external_ids": external_ids,
    })

_CATEGORY_OPTIONS = (
    {"value": MediaLibraryCategory.JAPANESE_KOREAN.value, "label": "日韩"},
    {"value": MediaLibraryCategory.DOMESTIC.value, "label": "国产"},
    {"value": MediaLibraryCategory.WESTERN.value, "label": "欧美"},
)
_SOURCES_BY_CATEGORY: dict[str, dict[str, type[MetadataSource]]] = {
    MediaLibraryCategory.JAPANESE_KOREAN.value: {
        CkDownloadSource.name: CkDownloadSource,
        HunkChSource.name: HunkChSource,
        JgvdataSource.name: JgvdataSource,
        KoShopSource.name: KoShopSource,
        MensrushSource.name: MensrushSource,
        AcceedSource.name: AcceedSource,
        BoyStudioSource.name: BoyStudioSource,
    },
    MediaLibraryCategory.DOMESTIC.value: {},
    MediaLibraryCategory.WESTERN.value: {},
}


def _source_for_product_number(category: str, product_number: str | None) -> str:
    """根据分类和番号匹配默认数据源；新增规则统一放在这里。"""
    sources = _SOURCES_BY_CATEGORY.get(category, {})
    if not sources:
        return "未配置"
    if product_number and is_hunk_ch_product_number(product_number):
        if HunkChSource.name in sources:
            return HunkChSource.name
    if product_number and product_number.upper().startswith("BWB"):
        if KoShopSource.name in sources:
            return KoShopSource.name
    return next(iter(sources), "未配置")


def _source_for_search(
    category: str,
    keyword: str,
    requested_source: str,
    fallback_source: str,
) -> str:
    """为实际搜索选择数据源；番号规则优先于界面上的普通默认值。"""
    product_number = extract_product_number(keyword) or keyword.strip() or None
    matched_source = _source_for_product_number(category, product_number)
    if product_number and is_hunk_ch_product_number(product_number):
        return matched_source
    return requested_source or fallback_source or matched_source


def _path_from_payload(notification: LibraryNewNotificationModel, current_item: dict[str, Any] | None = None) -> str:
    """兼容不同 Webhook 载荷结构，提取 Emby 媒体路径。"""
    item = current_item or (notification.payload.get("Item", {}) if notification.payload else {})
    return str(item.get("Path") or notification.payload.get("Path") or "")


def _item_image_url(notification: LibraryNewNotificationModel, payload_item: dict[str, Any]) -> str | None:
    """使用 Emby 的 Item 图片接口构造队列封面地址。"""
    image_tags = payload_item.get("ImageTags") or {}
    tag = image_tags.get("Primary")
    item_id = str(notification.item_id or "")
    base_url = settings.get_emby_base_url()
    if not (tag and item_id and base_url):
        return None
    params = {"tag": str(tag)}
    if settings.EMBY_API_KEY:
        params["api_key"] = settings.EMBY_API_KEY
    return f"{base_url.rstrip('/')}/Items/{item_id}/Images/Primary?{urlencode(params)}"


def _before_item_image_url(item_id: str, before_item: dict[str, Any]) -> str | None:
    """根据 Emby 快照生成当前封面地址。"""
    image_tags = before_item.get("ImageTags") or {}
    tag = image_tags.get("Primary")
    base_url = settings.get_emby_base_url()
    if not (tag and item_id and base_url):
        return None
    params = {"tag": str(tag)}
    if settings.EMBY_API_KEY:
        params["api_key"] = settings.EMBY_API_KEY
    return f"{base_url.rstrip('/')}/Items/{item_id}/Images/Primary?{urlencode(params)}"


def _before_person_image_url(person: dict[str, Any]) -> str | None:
    """为当前 Emby 演员生成可直接展示的主图地址。"""
    person_id = person.get("Id") or person.get("id")
    tag = person.get("PrimaryImageTag")
    base_url = settings.get_emby_base_url()
    if not (person_id and tag and base_url):
        return None
    params = {"tag": str(tag)}
    if settings.EMBY_API_KEY:
        params["api_key"] = settings.EMBY_API_KEY
    return f"{base_url.rstrip('/')}/Items/{person_id}/Images/Primary?{urlencode(params)}"


def _with_person_image_urls(before_item: dict[str, Any]) -> dict[str, Any]:
    """只为工作台响应补充图片地址，不改变后续写入用的原始快照。"""
    response_item = dict(before_item)
    people = before_item.get("People")
    if isinstance(people, list):
        response_item["People"] = [
            {**person, **({"ImageUrl": image_url} if (image_url := _before_person_image_url(person)) else {})}
            if isinstance(person, dict) else person
            for person in people
        ]
    return response_item


def _item_emby_url(item_id: str | None) -> str | None:
    """生成 Emby Web 中对应 Item 的详情页地址。"""
    base_url = settings.get_emby_base_url()
    if not base_url or not item_id:
        return None
    url = f"{base_url.rstrip('/')}/web/index.html#!/item?id={quote(str(item_id))}"
    if settings.EMBY_SERVER_ID:
        url += f"&serverId={quote(settings.EMBY_SERVER_ID)}"
    return url


def _queue_item(
    notification: LibraryNewNotificationModel,
    current_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """把新媒体通知转换为前端队列的数据结构。"""
    path = _path_from_payload(notification, current_item)
    payload_item = current_item or (notification.payload.get("Item", {}) if notification.payload else {})
    if "日韩" in path:
        category = "japanese_korean"
        category_label = "日韩"
    elif "欧美" in path:  # 假设路径中包含“欧美”字样则为欧美分类
        category = "western"
        category_label = "欧美"
    else:
        category = "domestic"
        category_label = "国产"

    item_name = str(
        (current_item or {}).get("Name")
        or notification.item_name
        or notification.title
        or "未命名条目"
    )
    extracted_number = extract_product_number(item_name)
    search_keyword = normalize_search_keyword(extracted_number or item_name)
    source = _source_for_product_number(category, extracted_number)
    return {
        "notification_id": str(notification.id),
        "item_id": notification.item_id or "",
        "emby_url": _item_emby_url(notification.item_id),
        "item_name": item_name,
        "path": path,
        "category": category,
        "category_label": category_label,
        "source": source,
        "status": "pending" if notification.status == "pending_completion" else notification.status or "pending",
        "search_keyword": search_keyword,
        "search_count": len(_search_cache.get(str(notification.id), [])),
        "image_url": _item_image_url(notification, payload_item),
        "category_options": _CATEGORY_OPTIONS,
        "source_options": [
            {"value": name, "label": name}
            for name in _SOURCES_BY_CATEGORY[category]
        ],
        "source_options_by_category": {
            category_name: [
                {"value": name, "label": name}
                for name in sources
            ]
            for category_name, sources in _SOURCES_BY_CATEGORY.items()
        },
    }


async def _get_notification(notification_id: str) -> LibraryNewNotificationModel:
    try:
        primary_key = int(notification_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="队列项目不存在") from error
    async with sessionmaker() as session:
        notification = await session.get(LibraryNewNotificationModel, primary_key)
        if notification is None:
            raise HTTPException(status_code=404, detail="队列项目不存在")
        return notification


async def get_queue() -> dict[str, Any]:
    """返回符合元数据补全条件的电影通知队列。"""
    async with sessionmaker() as session:
        result = await session.execute(
            select(LibraryNewNotificationModel)
            .where(LibraryNewNotificationModel.status == "pending_completion")
            .where(LibraryNewNotificationModel.item_type == "Movie")
            .order_by(LibraryNewNotificationModel.id.desc())
        )
        notifications = list(result.scalars())
    async def load_current_item(notification: LibraryNewNotificationModel) -> dict[str, Any]:
        if not notification.item_id:
            return {}
        try:
            _, item = await fetch_item_snapshot(notification.item_id)
            return item
        except Exception:
            return {}

    current_items = await asyncio.gather(*(load_current_item(notification) for notification in notifications))
    items = [_queue_item(notification, current_item) for notification, current_item in zip(notifications, current_items)]
    return {"items": items, "total": len(items)}


def _resolve_source(category: str, source_name: str) -> MetadataSource:
    """只允许使用后端注册且属于所选分类的数据源。"""
    source_class = _SOURCES_BY_CATEGORY.get(category, {}).get(source_name)
    if source_class is None:
        raise HTTPException(status_code=400, detail="该分类尚未配置所选数据源")
    return source_class()


async def search_queue(selections: list[dict[str, str]]) -> list[dict[str, Any]]:
    """搜索选中项目，缓存轻量候选结果供本次工作台会话使用。"""
    response: list[dict[str, Any]] = []
    for selection in selections:
        notification_id = selection["notification_id"]
        item = _queue_item(await _get_notification(notification_id))
        requested_keyword = selection["keyword"].strip()
        keyword = normalize_search_keyword(requested_keyword or item["search_keyword"])
        source_name = _source_for_search(
            selection["category"],
            selection["keyword"] or item["search_keyword"],
            selection["source"],
            item["source"],
        )
        if source_name == BoyStudioSource.name and (
            not requested_keyword or requested_keyword == item["search_keyword"]
        ):
            keyword = item["item_name"]
        source = _resolve_source(selection["category"], source_name)
        try:
            results = await source.search(keyword)
        except Exception as error:
            raise HTTPException(status_code=502, detail=f"数据源搜索失败：{error}") from error
        serialized = [result.model_dump(mode="json") for result in results]
        _search_cache[notification_id] = serialized
        response.append({"notification_id": notification_id, "results": serialized})
    return response


async def get_candidate(source: str, source_id: str) -> MetadataCandidate:
    """按来源和来源 ID 获取用户明确选择的候选详情。"""
    source_class = next(
        (
            source_class
            for sources in _SOURCES_BY_CATEGORY.values()
            for name, source_class in sources.items()
            if name == source
        ),
        None,
    )
    if source_class is None:
        raise HTTPException(status_code=404, detail="不支持的数据源")
    try:
        return await source_class().fetch_detail(source_id)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"候选详情抓取失败：{error}") from error


async def get_merged_candidate(
    primary_source: str,
    primary_source_id: str,
    supplement_source: str,
    supplement_source_id: str,
) -> MetadataCandidate:
    primary = await get_candidate(primary_source, primary_source_id)
    supplement = await get_candidate(supplement_source, supplement_source_id)
    return merge_metadata_candidates(primary, supplement)


async def get_candidate_preview(
    notification_id: str,
    source: str,
    source_id: str,
) -> dict[str, Any]:
    """返回候选与当前 Emby 元数据快照，供工作台逐字段比较。"""
    notification = await _get_notification(notification_id)
    if not notification.item_id:
        raise HTTPException(status_code=400, detail="队列项目缺少 Emby Item ID")
    candidate = await get_candidate(source, source_id)
    candidate.parse_report = {field: value for field, value in candidate.model_dump(mode="json").items() if field != "parse_report"}
    preview = await preview_metadata_candidate_update(notification.item_id, candidate)
    candidate.current_image_url = _before_item_image_url(
        notification.item_id,
        preview["before_item"],
    )
    return {"candidate": candidate.model_dump(mode="json"), "before_item": _with_person_image_urls(preview["before_item"])}


async def get_merged_candidate_preview(
    notification_id: str,
    primary_source: str,
    primary_source_id: str,
    supplement_source: str,
    supplement_source_id: str,
) -> dict[str, Any]:
    notification = await _get_notification(notification_id)
    if not notification.item_id:
        raise HTTPException(status_code=400, detail="队列项目缺少 Emby Item ID")
    candidate = await get_merged_candidate(primary_source, primary_source_id, supplement_source, supplement_source_id)
    candidate.parse_report = {field: value for field, value in candidate.model_dump(mode="json").items() if field != "parse_report"}
    preview = await preview_metadata_candidate_update(notification.item_id, candidate)
    candidate.current_image_url = _before_item_image_url(notification.item_id, preview["before_item"])
    return {"candidate": candidate.model_dump(mode="json"), "before_item": _with_person_image_urls(preview["before_item"])}


async def proxy_source_image(url: str, referer: str | None = None) -> tuple[bytes, str]:
    """通过带请求头的下载器代理数据源图片，避免浏览器防盗链拦截。"""
    try:
        source = CkDownloadSource()
        verify_ssl = "ko-shop.com" not in url.lower()
        return await download_image(
            url,
            referer=referer,
            extra_headers=source.image_headers(referer),
            verify_ssl=verify_ssl,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"图片加载失败：{error}") from error


async def writeback(
    notification_id: str,
    candidate: MetadataCandidate,
    *,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """将候选数据写入 Emby 通知状态不改变。"""
    notification = await _get_notification(notification_id)
    if not notification.item_id:
        raise HTTPException(status_code=400, detail="队列项目缺少 Emby Item ID")
    try:
        result = await apply_metadata_candidate_to_item(
            notification.item_id,
            candidate,
            fields=set(fields) if fields else None,
            overwrite=True,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Emby 写入失败：{error}") from error
    return result or {}
