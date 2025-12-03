import contextlib
from pathlib import Path

from aiogram import Router, types
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models import UserModel
from bot.keyboards.inline.start_admin import get_start_admin_keyboard
from bot.keyboards.inline.start_owner import get_start_owner_keyboard
from bot.keyboards.inline.start_user import get_start_user_keyboard
from bot.services.analytics import analytics
from bot.services.config_service import list_features
from bot.services.main_message import MainMessageService
from bot.utils.hitokoto import build_start_caption, fetch_hitokoto
from bot.utils.permissions import _resolve_role

router = Router(name="start")


def determine_role(user_id: int) -> str:
    """角色判定

    功能说明:
    - 基于配置判断角色, 返回 "owner" | "admin" | "user"

    输入参数:
    - user_id: Telegram 用户ID

    返回值:
    - str: 角色标识
    """
    with contextlib.suppress(Exception):
        if user_id == settings.get_owner_id():
            return "owner"
        if user_id in set(settings.get_admin_ids()):
            return "admin"
    return "user"


def get_common_image() -> str:
    """通用图片选择器

    功能说明:
    - 返回统一使用的主消息图片路径, 不依赖角色
    - 若图片不存在, 返回空字符串, 调用方仅编辑文本

    输入参数:
    - 无

    返回值:
    - str: 图片文件路径; 若不可用则返回空字符串
    """
    target = Path("assets/ui/start.jpg")
    return str(target) if target.exists() else ""


async def build_home_view(session: AsyncSession | None, user_id: int | None) -> tuple[str, types.InlineKeyboardMarkup]:
    """构建首页文案与键盘

    功能说明:
    - 拉取一言内容并生成首页文案(含项目名)
    - 根据数据库中的用户角色返回对应首页键盘

    输入参数:
    - session: 异步数据库会话, 可为 None
    - user_id: Telegram 用户ID, 可为 None

    返回值:
    - tuple[str, InlineKeyboardMarkup]: (caption, keyboard)
    """
    payload = await fetch_hitokoto(session, created_by=user_id)
    user_name = "(ง •̀_•́)ง"
    if session is not None and user_id is not None:
        with contextlib.suppress(Exception):
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = result.scalar_one_or_none()
            if user is not None:
                user_name = user.get_full_name()

    caption = build_start_caption(payload, user_name, settings.PROJECT_NAME)

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


@router.callback_query(lambda c: c.data == "home:back")
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
