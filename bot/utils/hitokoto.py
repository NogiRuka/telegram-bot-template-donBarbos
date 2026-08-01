from __future__ import annotations
import time
from typing import TYPE_CHECKING, Any

from bot.utils.http import HttpRequestError
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from bot.core.hitokoto import get_hitokoto_client

from bot.database.models.hitokoto import HitokotoModel
from bot.services.config_service import get_config
from bot.utils.text import escape_markdown_v2

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

SNIPPET_MAX_LEN = 48


async def fetch_hitokoto(session: AsyncSession | None, created_by: int | None = None) -> dict[str, Any] | None:
    """获取一言句子"""
    if session is not None:
        categories: list[str] | None = await get_config(session, "admin.hitokoto.categories")
    else:
        categories = ["d", "i"]

    try:
        start_time = time.perf_counter()

        client = get_hitokoto_client()
        payload = await client.request(
            "GET",
            "/",
            params={
                "encode": "json",
                "c": categories,
            }
        )
        if not isinstance(payload, dict):
            logger.warning(
                "⚠️ [Hitokoto] 返回格式异常: {}",
                type(payload),
            )
            return None
        u = payload.get("uuid")
        t = payload.get("type")
        ln = payload.get("length")
        duration_ms = int(
            (time.perf_counter() - start_time) * 1000
        )
        snippet = str(payload.get("hitokoto") or "")
        snippet = (snippet[:SNIPPET_MAX_LEN] + "…") if len(snippet) > SNIPPET_MAX_LEN else snippet
        logger.info(
            "🟢 [Hitokoto] 响应耗时={}ms",
            duration_ms
        )
        logger.info(
            "📦 [Hitokoto] 数据 uuid={} | type={} | length={} | 片段='{}'",
            u,
            t,
            ln,
            snippet,
        )
        try:
            uuid = str(payload.get("uuid") or "")
            if uuid and session:
                model = build_hitokoto_model(payload, created_by)
                session.add(model)
                await session.commit()
        except SQLAlchemyError as err:
                if session:
                    await session.rollback()
                logger.exception(
                    "🔴 [Hitokoto] 入库失败: {}",
                    err,
                )
        return payload
    except (TimeoutError, HttpRequestError) as exc:
        logger.warning(f"⚠️ [Hitokoto] 请求失败: {exc}")
        return None

def build_hitokoto_model(
    payload: dict[str, Any],
    created_by: int | None,
) -> HitokotoModel:
    uuid = str(payload.get("uuid") or "")
    return HitokotoModel(
            uuid=uuid,
            hitokoto_id=int(payload.get("id") or 0) or None,
            hitokoto=str(payload.get("hitokoto") or ""),
            type=str(payload.get("type") or "") or None,
            from_=str(payload.get("from") or "") or None,
            from_who=str(payload.get("from_who") or "") or None,
            creator=str(payload.get("creator") or "") or None,
            creator_uid=int(payload.get("creator_uid") or 0) or None,
            reviewer=int(payload.get("reviewer") or 0) or None,
            commit_from=str(payload.get("commit_from") or "") or None,
            source_created_at=str(payload.get("created_at") or "") or None,
            length=int(payload.get("length") or 0) or None,
            created_by=created_by,
            updated_by=created_by,
        )

def build_start_caption(
    payload: dict[str, Any] | None,
    user_name: str,
    announcement: str | None = None,
) -> str:
    """构建欢迎页文案

    功能说明:
    - 复用原始欢迎页模板, 使用 Markdown 链接与强调样式
    - 可附加公告文案(存在时显示, 不存在则不显示)
    """
    hitokoto_raw = "(ง •̀_•́)ง" if not payload else str(payload.get("hitokoto") or "(ง •̀_•́)ง")
    # 链接文本需进行 MarkdownV2 转义，避免包含特殊字符导致解析失败
    hitokoto = escape_markdown_v2(hitokoto_raw)
    uuid = "" if not payload else str(payload.get("uuid") or "")
    link = f"https://hitokoto.cn?uuid={uuid}" if uuid else "https://hitokoto.cn/"
    # 用户名与项目名也需要转义
    user_name_esc = escape_markdown_v2(user_name)
    # project_name_esc = escape_markdown_v2(project_name)
    base = f"『 [{hitokoto}]({link}) 』\n\n🍃 嗨  *_{user_name_esc}_*\n🎐 很高兴见到你\n"
    # base = f"『 [{hitokoto}]({link}) 』\n\n🍃 嗨  *_{user_name_esc}_*\n"
    ann = ""
    if announcement:
        ann = f"\n📢 公告：\n{escape_markdown_v2(announcement)}\n"
    return f"{base}{ann}"
