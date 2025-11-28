from __future__ import annotations
import json
from typing import TYPE_CHECKING, Any

import aiohttp
from aiohttp import ClientError

from bot.services.config_service import get_config

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_hitokoto(session: AsyncSession) -> dict[str, Any] | None:
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
    categories: list[str] = await get_config(session, "admin.hitokoto.categories") or ["d", "i"]
    query = [("encode", "json")] + [("c", c) for c in categories]
    params = "&".join([f"{k}={v}" for k, v in query])
    url = f"https://v1.hitokoto.cn/?{params}"
    try:
        async with aiohttp.ClientSession() as http_session, http_session.get(
            url, timeout=aiohttp.ClientTimeout(total=6.0)
        ) as resp:
            data = await resp.text()
            return json.loads(data)
    except (ClientError, TimeoutError, json.JSONDecodeError):
        return None


def build_hitokoto_caption(payload: dict[str, Any] | None) -> str:
    """构建一言文案

    功能说明:
    - 将一言字典转换为主面板展示文案, 包含作者与来源信息

    输入参数:
    - payload: 一言返回字典; 可为 None

    返回值:
    - str: 适合直接发送的文本内容
    """
    if not payload:
        return "主面板"
    text = str(payload.get("hitokoto") or "主面板")
    source = str(payload.get("from") or "")
    author = str(payload.get("from_who") or "").strip()
    tail = f"\n— {author} · {source}" if source or author else ""
    return f"{text}{tail}"
