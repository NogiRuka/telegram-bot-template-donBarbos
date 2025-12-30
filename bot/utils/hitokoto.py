from __future__ import annotations
import json
import time
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp import ClientError
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from bot.database.database import sessionmaker
from bot.database.models.hitokoto import HitokotoModel
from bot.services.config_service import get_config
from bot.utils.text import escape_markdown_v2

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

SNIPPET_MAX_LEN = 48


async def fetch_hitokoto(session: AsyncSession | None, created_by: int | None = None) -> dict[str, Any] | None:
    """获取一言句子

    功能说明:
    - 读取管理员配置 `admin.hitokoto.categories`, 请求 Hitokoto 接口并返回 JSON 字典

    输入参数:
    - session: 异步数据库会话
    - created_by: 创建/更新操作者用户ID, 用于审计字段

    返回值:
    - dict[str, Any] | None: 一言返回字典; 异常或解析失败返回 None

    依赖:
    - aiohttp: `pip install aiohttp`
    """
    if session is not None:
        categories: list[str] | None = await get_config(session, "admin.hitokoto.categories")
    else:
        categories = ["d", "i"]
    query = [("encode", "json")] + ([("c", c) for c in categories] if categories else [])
    params = "&".join([f"{k}={v}" for k, v in query])
    url = f"https://v1.hitokoto.cn/?{params}"
    # logger.info(f"🔎 [Hitokoto] 请求 URL={url} | 分类={categories}")
    try:
        start_time = time.perf_counter()
        async with (
            aiohttp.ClientSession() as http_session,
            http_session.get(url, timeout=aiohttp.ClientTimeout(total=6.0)) as resp,
        ):
            data = await resp.text()
            payload = json.loads(data)
            u = payload.get("uuid")
            t = payload.get("type")
            ln = payload.get("length")
            int((time.perf_counter() - start_time) * 1000)
            snippet = str(payload.get("hitokoto") or "")
            snippet = (snippet[:SNIPPET_MAX_LEN] + "…") if len(snippet) > SNIPPET_MAX_LEN else snippet
            # logger.info(f"🟢 [Hitokoto] 响应 status={resp.status} | 耗时={duration_ms}ms")
            logger.info(f"📦 [Hitokoto] 数据 uuid={u} | type={t} | length={ln} | 片段='{snippet}'")
            try:
                uuid = str(payload.get("uuid") or "")
                if uuid:
                    target_session = session
                    # 若外部没有提供会话, 使用短连接会话入库
                    if target_session is None:
                        async with sessionmaker() as auto_session:
                            target_session = auto_session
                            model = HitokotoModel(
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
                            target_session.add(model)
                            await target_session.commit()
                            # logger.info(f"🧾 [Hitokoto] 入库成功 id={model.id} uuid={uuid}")
                    else:
                        model = HitokotoModel(
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
                        target_session.add(model)
                        await target_session.commit()
                        # logger.info(f"🧾 [Hitokoto] 入库成功 id={model.id} uuid={uuid}")
            except SQLAlchemyError as err:
                logger.exception(f"🔴 [Hitokoto] 入库失败: {err}")
            return payload
    except (ClientError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning(f"⚠️ [Hitokoto] 请求失败: {exc}")
        return None


def build_start_caption(
    payload: dict[str, Any] | None,
    user_name: str,
    project_name: str,
    announcement: str | None = None,
) -> str:
    """构建欢迎页文案

    功能说明:
    - 复用原始欢迎页模板, 使用 Markdown 链接与强调样式
    - 可附加公告文案(存在时显示, 不存在则不显示)

    输入参数:
    - payload: 一言返回字典; 可为 None
    - user_name: 用户显示名称
    - project_name: 项目名称
    - announcement: 公告文案; 可为 None

    返回值:
    - str: 用于 Markdown 解析模式的完整文案
    """
    hitokoto_raw = "(ง •̀_•́)ง" if not payload else str(payload.get("hitokoto") or "(ง •̀_•́)ง")
    # 链接文本需进行 MarkdownV2 转义，避免包含特殊字符导致解析失败
    hitokoto = escape_markdown_v2(hitokoto_raw)
    uuid = "" if not payload else str(payload.get("uuid") or "")
    link = f"https://hitokoto.cn?uuid={uuid}" if uuid else "https://hitokoto.cn/"
    # 用户名与项目名也需要转义
    user_name_esc = escape_markdown_v2(user_name)
    project_name_esc = escape_markdown_v2(project_name)
    base = f"『 [{hitokoto}]({link}) 』\n\n🍃 嗨  *_{user_name_esc}_*\n🎐 欢迎使用{project_name_esc}\n"
    ann = ""
    if announcement:
        ann = f"\n📢 公告：\n{escape_markdown_v2(announcement)}\n"
    return f"{base}{ann}"
