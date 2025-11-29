from __future__ import annotations
import os
from typing import Any

from aiogram import Router, types
from aiogram.filters import Command

from bot.services.emby_client import EmbyClient, EmbyNotConfiguredError, emby
from bot.core.config import settings

router = Router(name="emby")


def _get_emby_client() -> EmbyClient | None:
    """构建 Emby 客户端实例

    功能说明:
    - 从配置读取 `EMBY_BASE_URL` 与 `EMBY_API_KEY`, 构建 `EmbyClient`

    输入参数:
    - 无

    返回值:
    - EmbyClient | None: 成功返回客户端实例, 缺少配置返回 None
    """
    base_url = settings.get_emby_base_url()
    api_key = settings.get_emby_api_key()
    if not base_url or not api_key:
        return None
    return EmbyClient(base_url, api_key)


@router.message(Command("emby_users"))
async def list_emby_users(message: types.Message) -> None:
    """列出 Emby 用户

    功能说明:
    - 通过 Emby API 获取用户列表并展示名称

    输入参数:
    - message: Telegram 消息对象

    返回值:
    - None

    依赖安装:
    - pip install aiohttp[speedups]

    Telegram API 限制:
    - 单条消息长度约 4096 字符, 用户过多需分页或截断
    - 频繁调用可能触发限流, 建议设置命令使用频率
    """
    try:
        users: list[dict[str, Any]] = await emby.get_users()
        names = [str(u.get("Name") or u.get("name") or "") for u in users]
        names = [n for n in names if n]
        text = "\n".join(names) if names else "(空)"
        await message.answer(f"当前用户列表:\n{text}")
    except EmbyNotConfiguredError:
        await message.answer(
            "❌ 未配置 Emby 连接信息\n"
            "请在 .env 文件中设置 EMBY_BASE_URL 与 EMBY_API_KEY"
        )
    except Exception as e:
        await message.answer(f"❌ 获取 Emby 用户失败: {e!s}")
