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
    hitokoto = "主面板" if not payload else str(payload.get("hitokoto") or "主面板")
    uuid = "" if not payload else str(payload.get("uuid") or "")
    link = f"https://hitokoto.cn?uuid={uuid}" if uuid else "https://hitokoto.cn/"
    safe_text = html_escape(hitokoto)
    safe_user = html_escape(user_name)
    return (
        f'『 <a href="{link}">{safe_text}</a> 』\n\n'
        f"🍃 嗨  <b><i>{safe_user}</i></b>\n"
        f"🎐 欢迎使用{project_name}~\n"
    )
