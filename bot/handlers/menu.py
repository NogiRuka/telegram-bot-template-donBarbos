import contextlib
import json
from pathlib import Path
from urllib.parse import urlencode

import aiohttp
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InputMediaPhoto
from aiohttp import ClientError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.hitokoto import HitokotoModel
from bot.keyboards.inline.menu import main_keyboard
from bot.services.config_service import get_config

router = Router(name="menu")


async def render_view(
    message: types.Message,
    image_path: str,
    caption: str,
    keyboard: types.InlineKeyboardMarkup,
) -> bool:
    """统一渲染视图

    功能说明:
    - 始终编辑已有主消息以更新图片、说明与键盘

    输入参数:
    - message: Telegram消息对象
    - image_path: 图片路径
    - caption: 文本说明
    - keyboard: 内联键盘

    返回值:
    - bool: 是否成功编辑了主消息
    """
    p = Path(image_path)
    if p.exists():
        file = FSInputFile(str(p))
        media = InputMediaPhoto(media=file, caption=caption)
        with contextlib.suppress(Exception):
            await message.edit_media(media=media, reply_markup=keyboard)
            return True
        with contextlib.suppress(Exception):
            await message.edit_caption(caption, reply_markup=keyboard)
            return True
    with contextlib.suppress(Exception):
        await message.edit_text(text=caption, reply_markup=keyboard)
        return True
    return False


@router.message(Command(commands=["menu", "main"]))
async def menu_handler(message: types.Message, session: AsyncSession) -> None:
    """主菜单处理器

    功能说明:
    - 调用一言接口获取句子作为主面板文案并展示内联菜单

    输入参数:
    - message: Telegram消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    try:
        # 读取分类配置, 若为空则使用默认值 ["d", "i"]
        categories: list[str] = await get_config(session, "admin.hitokoto.categories") or ["d", "i"]
        query = [("encode", "json")] + [("c", c) for c in categories]
        url = f"https://v1.hitokoto.cn/?{urlencode(query)}"

        # 异步请求
        async with aiohttp.ClientSession() as http_session, http_session.get(
            url, timeout=aiohttp.ClientTimeout(total=6.0)
        ) as resp:
            data = await resp.text()
            payload = json.loads(data)

        # 保存到数据库
        async def _save_sentence(session_obj: AsyncSession, body: dict[str, object]) -> None:
            """保存一言到数据库

            功能说明:
            - 将命中的一言字段映射到 `hitokoto` 表

            输入参数:
            - session_obj: 异步数据库会话
            - body: 一言字典

            返回值:
            - None
            """
            try:
                model = HitokotoModel(
                    hitokoto_id=int(body.get("id") or 0) or None,
                    uuid=str(body.get("uuid") or "") or None,
                    hitokoto=str(body.get("hitokoto") or ""),
                    type=str(body.get("type") or "") or None,
                    source=str(body.get("from") or "") or None,
                    from_who=str(body.get("from_who") or "") or None,
                    creator=str(body.get("creator") or "") or None,
                    creator_uid=int(body.get("creator_uid") or 0) or None,
                    reviewer=int(body.get("reviewer") or 0) or None,
                    commit_from=str(body.get("commit_from") or "") or None,
                    source_created_at=str(body.get("created_at") or "") or None,
                    length=int(body.get("length") or 0) or None,
                )
                session_obj.add(model)
                await session_obj.commit()
            except SQLAlchemyError:
                with contextlib.suppress(SQLAlchemyError):
                    await session_obj.rollback()

        await _save_sentence(session, payload)

        # 渲染主面板文案
        text = str(payload.get("hitokoto") or "主面板")
        source = str(payload.get("from") or "")
        author = str(payload.get("from_who") or "").strip()
        tail = f"\n— {author} · {source}" if source or author else ""
        await message.answer(f"{text}{tail}", reply_markup=main_keyboard())
    except (ClientError, TimeoutError, json.JSONDecodeError):
        await message.answer("主面板", reply_markup=main_keyboard())
