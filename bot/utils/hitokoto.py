from __future__ import annotations
import json
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp import ClientError
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from bot.database.models.hitokoto import HitokotoModel
from bot.services.config_service import get_config

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

async def fetch_hitokoto(session: AsyncSession, created_by: int | None = None) -> dict[str, Any] | None:
    """获取一言句子

    功能说明:
    - 读取管理员配置 `admin.hitokoto.categories`, 请求 Hitokoto 接口并返回 JSON 字典

    输入参数:
    - session: 异步数据库会话

    返回值:
    - dict[str, Any] | None: 一言返回字典; 异常或解析失败返回 None

    依赖:
    - aiohttp: `pip install aiohttp`
    """
    categories: list[str] = await get_config(session, "admin.hitokoto.categories")
    query = [("encode", "json")] + [("c", c) for c in categories]
    params = "&".join([f"{k}={v}" for k, v in query])
    url = f"https://v1.hitokoto.cn/?{params}"
    logger.info("[Hitokoto] 请求URL={} 分类={}", url, categories)
    try:
        async with aiohttp.ClientSession() as http_session, http_session.get(
            url, timeout=aiohttp.ClientTimeout(total=6.0)
        ) as resp:
            data = await resp.text()
            payload = json.loads(data)
            u = payload.get("uuid")
            t = payload.get("type")
            ln = payload.get("length")
            logger.info("[Hitokoto] 拉取成功 uuid={} type={} length={}", u, t, ln)
            try:
                uuid = str(payload.get("uuid") or "")
                if uuid:
                    exists = await session.get(HitokotoModel, uuid)
                    if exists is None:
                        model = HitokotoModel(
                            uuid=uuid,
                            id=int(payload.get("id") or 0) or None,
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
                        session.add(model)
                        await session.commit()
                        logger.info("[Hitokoto] 已入库 uuid={}", uuid)
                    else:
                        exists.hitokoto = str(payload.get("hitokoto") or exists.hitokoto)
                        exists.type = str(payload.get("type") or exists.type)
                        exists.from_ = str(payload.get("from") or exists.from_)
                        exists.from_who = str(payload.get("from_who") or exists.from_who)
                        exists.creator = str(payload.get("creator") or exists.creator)
                        exists.creator_uid = int(payload.get("creator_uid") or (exists.creator_uid or 0)) or None
                        exists.reviewer = int(payload.get("reviewer") or (exists.reviewer or 0)) or None
                        exists.commit_from = str(payload.get("commit_from") or exists.commit_from)
                        exists.source_created_at = str(payload.get("created_at") or exists.source_created_at)
                        exists.length = int(payload.get("length") or (exists.length or 0)) or None
                        exists.updated_by = created_by
                        await session.commit()
                        logger.info("[Hitokoto] 已更新 uuid={}", uuid)
            except SQLAlchemyError:
                logger.exception("[Hitokoto] 入库失败")
            return payload
    except (ClientError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Hitokoto 请求失败: %s", exc)
        return None


def html_escape(text: str) -> str:
    """HTML转义

    功能说明:
    - 对文本进行基本的 HTML 字符转义, 防止解析错误

    输入参数:
    - text: 原始文本

    返回值:
    - str: 转义后的文本
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_start_caption(payload: dict[str, Any] | None, user_name: str, project_name: str) -> str:
    """构建欢迎页文案

    功能说明:
    - 复用原始欢迎页模板, 将超链接替换为一言文本以及 UUID 链接

    输入参数:
    - payload: 一言返回字典; 可为 None
    - user_name: 用户显示名称
    - project_name: 项目名称

    返回值:
    - str: 用于 HTML 解析模式的完整文案
    """
    hitokoto = "(ง •̀_•́)ง" if not payload else str(payload.get("hitokoto") or "(ง •̀_•́)ง")
    uuid = "" if not payload else str(payload.get("uuid") or "")
    link = f"https://hitokoto.cn?uuid={uuid}" if uuid else "https://hitokoto.cn/"
    safe_text = html_escape(hitokoto)
    safe_user = html_escape(user_name)
    return (
        f'『 <a href="{link}">{safe_text}</a> 』\n\n'
        f"🍃 嗨  <b><i>{safe_user}</i></b>\n"
        f"🎐 欢迎使用{project_name}~\n"
    )
