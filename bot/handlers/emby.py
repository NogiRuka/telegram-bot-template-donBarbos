from __future__ import annotations
import asyncio
from typing import Any

from aiogram import Router, types
from aiogram.filters import Command
from aiohttp import ClientError

from bot.core.config import settings
from bot.services.emby_client import EmbyClient

router = Router(name="emby")
CREATE_MIN_ARGS = 2
CREATE_PASS_INDEX = 2
DELETE_MIN_ARGS = 2
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

    client = _get_emby_client()
    if client is None:
        await message.answer(
            "❌ 未配置 Emby 连接信息\n"
            "请在 .env 文件中设置 EMBY_BASE_URL 与 EMBY_API_KEY"
        )
        return
    try:
        users: list[dict[str, Any]] = await client.get_users()
        names = [str(u.get("Name") or u.get("name") or "") for u in users]
        names = [n for n in names if n]
        text = "\n".join(names) if names else "(空)"
        await message.answer(f"当前用户列表:\n{text}")
    except (ClientError, asyncio.TimeoutError) as e:
        await message.answer(f"❌ 获取 Emby 用户失败: {e!s}")


@router.message(Command("emby_create"))
async def create_emby_user(message: types.Message) -> None:
    """创建 Emby 用户

    功能说明:
    - 使用 `/emby_create <name> [password]` 创建用户
    - 若配置了 `EMBY_TEMPLATE_USER_ID`, 将复制该用户的策略与配置

    输入参数:
    - message: Telegram 消息对象

    返回值:
    - None
    """
    client = _get_emby_client()
    if client is None:
        await message.answer(
            "❌ 未配置 Emby 连接信息\n"
            "请在 .env 文件中设置 EMBY_BASE_URL 与 EMBY_API_KEY"
        )
        return
    parts = (message.text or "").strip().split()
    if len(parts) < CREATE_MIN_ARGS:
        await message.answer("用法: /emby_create <name> [password]")
        return
    name = parts[1]
    password = parts[2] if len(parts) >= CREATE_PASS_INDEX else None
    try:
        template_id = settings.get_emby_template_user_id()
        user_copy_options = ["UserPolicy", "UserConfiguration"] if template_id else None
        res = await client.create_user(
            name=name,
            password=password,
            copy_from_user_id=template_id,
            user_copy_options=user_copy_options,
        )
        uid = str(res.get("Id") or "")
        created_name = str(res.get("Name") or name)
        await message.answer(f"✅ 创建成功: {created_name} (ID: {uid})")
    except (ClientError, asyncio.TimeoutError) as e:
        await message.answer(f"❌ 创建失败: {e!s}")


@router.message(Command("emby_delete"))
async def delete_emby_user(message: types.Message) -> None:
    """删除 Emby 用户

    功能说明:
    - 使用 `/emby_delete <user_id>` 删除用户

    输入参数:
    - message: Telegram 消息对象

    返回值:
    - None
    """
    client = _get_emby_client()
    if client is None:
        await message.answer(
            "❌ 未配置 Emby 连接信息\n"
            "请在 .env 文件中设置 EMBY_BASE_URL 与 EMBY_API_KEY"
        )
        return
    parts = (message.text or "").strip().split()
    if len(parts) < DELETE_MIN_ARGS:
        await message.answer("用法: /emby_delete <user_id>")
        return
    user_id = parts[1]
    try:
        await client.delete_user(user_id)
        await message.answer(f"✅ 已删除用户: {user_id}")
    except (ClientError, asyncio.TimeoutError) as e:
        await message.answer(f"❌ 删除失败: {e!s}")
