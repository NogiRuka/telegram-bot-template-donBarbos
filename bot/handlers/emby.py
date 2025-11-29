from __future__ import annotations
import os
from typing import Any

from aiogram import Router, types
from aiogram.filters import Command

from bot.services.emby_client import EmbyClient
from bot.services.emby_user_service import EmbyUserService

router = Router(name="emby")


def _get_emby_service() -> EmbyUserService | None:
    """构建 Emby 服务实例

    功能说明:
    - 从环境变量读取 `EMBY_BASE_URL` 与 `EMBY_API_KEY`, 构建 `EmbyUserService`

    输入参数:
    - 无

    返回值:
    - EmbyUserService | None: 成功返回服务实例, 缺少配置返回 None
    """
    base_url = os.getenv("EMBY_BASE_URL")
    api_key = os.getenv("EMBY_API_KEY")
    if not base_url or not api_key:
        return None
    return EmbyUserService(EmbyClient(base_url, api_key))


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
    service = _get_emby_service()
    if service is None:
        await message.answer(
            "❌ 未配置 Emby 连接信息\n"
            "请在环境变量中设置 EMBY_BASE_URL 与 EMBY_API_KEY"
        )
        return
    try:
        users: list[dict[str, Any]] = await service.list_users()
        names = [str(u.get("Name") or u.get("name") or "") for u in users]
        names = [n for n in names if n]
        text = "\n".join(names) if names else "(空)"
        await message.answer(f"当前用户列表:\n{text}")
    except Exception as e:
        await message.answer(f"❌ 获取 Emby 用户失败: {e!s}")

