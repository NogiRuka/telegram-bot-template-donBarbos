from __future__ import annotations
import asyncio
import datetime as _dt
from typing import TYPE_CHECKING, Any

from aiogram import Router, types
from aiogram.filters import Command
from aiohttp import ClientError
from loguru import logger

try:
    import bcrypt
except ModuleNotFoundError:  # pragma: no cover
    bcrypt = None  # type: ignore[assignment]
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from bot.core.config import settings
from bot.database.models import EmbyUserHistoryModel, EmbyUserModel
from bot.services.emby_service import get_client

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from bot.core.emby import EmbyClient

router = Router(name="emby")


async def get_client_or_reply(message: types.Message) -> EmbyClient | None:
    """获取 EmbyClient 或回复缺少配置

    功能说明:
    - 从配置构建 EmbyClient, 若缺少配置则直接回复提示

    输入参数:
    - message: Telegram 消息对象

    返回值:
    - EmbyClient | None: 成功返回客户端, 失败返回 None
    """
    client = get_client()
    if client is None:
        message_text = "❌ 未配置 Emby 连接信息\n请在 .env 文件中设置 EMBY_BASE_URL 与 EMBY_API_KEY"
        await message.answer(message_text)
        return None
    return client


async def get_args_or_usage(message: types.Message, usage: str, min_args: int) -> list[str] | None:
    """解析命令参数, 不足则回复用法

    功能说明:
    - 解析消息文本为空格分隔参数, 不满足最小数量则回复用法

    输入参数:
    - message: Telegram 消息对象
    - usage: 用法提示文本
    - min_args: 最少参数数量

    返回值:
    - list[str] | None: 参数列表, 不足返回 None
    """
    parts = (message.text or "").strip().split()
    need = int(min_args)
    if len(parts) < need:
        await message.answer(usage)
        return None
    return parts


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

    client = await get_client_or_reply(message)
    if client is None:
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
async def create_emby_user(message: types.Message, session: AsyncSession) -> None:
    """创建 Emby 用户

    功能说明:
    - 使用 `/emby_create <name> [password]` 创建用户
    - 若配置了 `EMBY_TEMPLATE_USER_ID`, 将复制该用户的策略与配置

    输入参数:
    - message: Telegram 消息对象

    返回值:
    - None
    """
    client = await get_client_or_reply(message)
    if client is None:
        return
    parts = await get_args_or_usage(message, "用法: /emby_create <name> [password]", 2) or []
    name_idx, pass_idx = 1, 2
    if not parts:
        return
    name = parts[name_idx]
    password = parts[pass_idx] if len(parts) > pass_idx else None
    try:
        template_id = settings.get_emby_template_user_id()
        res = await client.create_user(
            name=name,
            copy_from_user_id=template_id,
        )
        uid = str(res.get("Id") or "")
        created_name = str(res.get("Name") or name)
        try:
            pwd_hash = hash_password(password)
            model = EmbyUserModel(
                emby_user_id=uid,
                name=created_name,
                user_dto=res,
                password_hash=pwd_hash,
            )
            history = EmbyUserHistoryModel(
                emby_user_id=uid,
                name=created_name,
                user_dto=res,
                password_hash=pwd_hash,
                action="create",
            )
            session.add(model)
            session.add(history)
            await session.commit()
        except SQLAlchemyError as e:
            logger.exception(f"❌ 写入 Emby 用户到数据库失败: {e!s}")
        await message.answer(f"✅ 创建成功: {created_name} (ID: {uid})")
    except (ClientError, asyncio.TimeoutError) as e:
        await message.answer(f"❌ 创建失败: {e!s}")


@router.message(Command("emby_delete"))
async def delete_emby_user(message: types.Message, session: AsyncSession) -> None:
    """删除 Emby 用户

    功能说明:
    - 使用 `/emby_delete <user_id>` 删除用户

    输入参数:
    - message: Telegram 消息对象

    返回值:
    - None
    """
    client = await get_client_or_reply(message)
    if client is None:
        return
    parts = await get_args_or_usage(message, "用法: /emby_delete <user_id>", 2) or []
    id_idx = 1
    if not parts:
        return
    user_id = parts[id_idx]
    try:
        await client.delete_user(user_id)
        try:
            res = await session.execute(select(EmbyUserModel).where(EmbyUserModel.emby_user_id == user_id))
            model = res.scalar_one_or_none()
            if model:
                model.is_deleted = True
                model.deleted_at = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
                history = EmbyUserHistoryModel(
                    emby_user_id=user_id,
                    name=model.name,
                    user_dto=model.user_dto,
                    password_hash=model.password_hash,
                    action="delete",
                )
                session.add(history)
                await session.commit()
        except SQLAlchemyError as e:
            logger.exception(f"❌ 标记 Emby 用户软删除失败: {e!s}")
        await message.answer(f"✅ 已删除用户: {user_id}")
    except (ClientError, asyncio.TimeoutError) as e:
        await message.answer(f"❌ 删除失败: {e!s}")


def hash_password(password: str | None) -> str | None:
    """密码哈希

    功能说明:
    - 使用 bcrypt 对明文密码进行哈希处理

    输入参数:
    - password: 明文密码或 None

    返回值:
    - str | None: 哈希后的密码或 None

    依赖安装:
    - pip install bcrypt
    """
    if not password:
        return None
    try:
        if bcrypt is None:
            logger.exception("❌ bcrypt 未安装")
            return None
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    except (ValueError, TypeError) as e:
        logger.exception(f"❌ bcrypt 哈希失败: {e!s}")
        return None
