import contextlib

from aiogram import F, Router, types
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ANNOUNCEMENT_TEXT
from bot.core.config import settings
from bot.database.models import UserModel
from bot.keyboards.inline.admin import get_start_admin_keyboard
from bot.keyboards.inline.owner import get_start_owner_keyboard
from bot.keyboards.inline.user import get_start_user_keyboard
from bot.services.analytics import analytics
from bot.services.config_service import get_config, list_features
from bot.services.main_message import MainMessageService
from bot.utils.hitokoto import build_start_caption, fetch_hitokoto
from bot.utils.images import get_common_image
from bot.utils.permissions import _resolve_role

router = Router(name="start")

from typing import Any

async def build_home_view(
    session: AsyncSession | None, 
    user_id: int | None, 
    append_text: str | None = None,
    hitokoto_payload: dict[str, Any] | None = None
) -> tuple[str, types.InlineKeyboardMarkup]:
    """构建首页文案与键盘

    功能说明:
    - 拉取一言内容并生成首页文案(含项目名)
    - 根据数据库中的用户角色返回对应首页键盘
    - 支持追加文本内容
    - 支持传入指定的一言内容(避免刷新)

    输入参数:
    - session: 异步数据库会话, 可为 None
    - user_id: Telegram 用户ID, 可为 None
    - append_text: 需追加的文本内容, 可为 None
    - hitokoto_payload: 指定的一言内容字典, 若提供则不重新拉取

    返回值:
    - tuple[str, InlineKeyboardMarkup]: (caption, keyboard)
    """
    if hitokoto_payload:
        payload = hitokoto_payload
    else:
        payload = await fetch_hitokoto(session, created_by=user_id)
    
    user_name = "(ง •̀_•́)ง"
    if session is not None and user_id is not None:
        with contextlib.suppress(Exception):
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one_or_none()
            if user is not None:
                user_name = user.get_full_name()

    announcement = None
    if session is not None:
        with contextlib.suppress(Exception):
            announcement = await get_config(session, KEY_ANNOUNCEMENT_TEXT)
            if isinstance(announcement, (dict, list, bool, int, float)):
                announcement = str(announcement)
            if announcement is not None:
                announcement = announcement.strip() or None

    caption = build_start_caption(payload, user_name, settings.PROJECT_NAME, announcement)

    if append_text:
        caption += f"\n\n{append_text}"

    role = await _resolve_role(session, user_id)
    kb_map = {
        "owner": get_start_owner_keyboard(),
        "admin": get_start_admin_keyboard(),
        "user": get_start_user_keyboard(),
    }
    keyboard = kb_map.get(role, kb_map["user"])
    return caption, keyboard


@router.message(CommandStart())
@analytics.track_event("Sign Up")
async def start_handler(message: types.Message, session: AsyncSession, main_msg: MainMessageService) -> None:
    """欢迎消息处理器

    功能说明:
    - 根据数据库中记录的用户角色显示首页界面与按钮

    输入参数:
    - message: Telegram消息对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    uid = message.from_user.id if message.from_user else None
    with contextlib.suppress(Exception):
        await list_features(session)

    # 构建与首次进入一致的首页文案与键盘
    caption, kb = await build_home_view(session, uid)

    image = get_common_image()
    await main_msg.send_main(message, image or None, caption, kb)


@router.callback_query(F.data == "back:home")
async def back_to_home(callback: types.CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """返回主面板

    功能说明:
    - 根据用户角色返回至对应的一级主页键盘

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    uid = callback.from_user.id if callback.from_user else None
    caption, kb = await build_home_view(session, uid)

    await main_msg.update_on_callback(callback, caption, kb, get_common_image())

    await callback.answer()
