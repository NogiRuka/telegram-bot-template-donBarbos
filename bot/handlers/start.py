
import contextlib
from pathlib import Path

from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.handlers.menu import render_view
from bot.keyboards.inline.start_admin import get_start_admin_keyboard
from bot.keyboards.inline.start_owner import get_start_owner_keyboard
from bot.keyboards.inline.start_user import get_start_user_keyboard
from bot.services.analytics import analytics
from bot.services.config_service import list_features
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


# 移除本地首页键盘构建函数, 统一复用键盘模块的构建函数


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


@router.message(CommandStart())
@analytics.track_event("Sign Up")
async def start_handler(message: types.Message, role: str | None = None, session: AsyncSession | None = None) -> None:
    """欢迎消息处理器

    功能说明:
    - 根据角色显示不同首页界面与按钮

    输入参数:
    - message: Telegram消息对象
    - role: 用户角色标识

    返回值:
    - None
    """
    if role is None:
        user = message.from_user
        uid = user.id if user else None
        role = determine_role(uid) if uid else "user"
    with contextlib.suppress(Exception):
        if session is not None:
            await list_features(session)

    # 拉取一言并按原模板构建文案
    payload = await fetch_hitokoto(session) if session is not None else None
    user_name = message.from_user.full_name if message.from_user else "旅人"
    caption = build_start_caption(payload, user_name, settings.PROJECT_NAME)

    # 根据角色选择键盘
    kb_map = {
        "owner": get_start_owner_keyboard(),
        "admin": get_start_admin_keyboard(),
        "user": get_start_user_keyboard(),
    }
    kb = kb_map.get(role, kb_map["user"])

    image = get_common_image()
    if image:
        file = FSInputFile(image)
        await message.answer_photo(photo=file, caption=caption, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(caption, reply_markup=kb, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "home:back")
async def back_to_home(callback: types.CallbackQuery, session: AsyncSession) -> None:
    """返回主面板

    功能说明:
    - 根据用户角色返回至对应的一级主页键盘

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    with contextlib.suppress(Exception):
        await list_features(session)
    user_id = callback.from_user.id if callback.from_user else None
    role = await _resolve_role(session, user_id)
    caption = (
        "🌸 桜色服务助手 | 欢迎页\n\n"
        "• 账号中心: 注册、信息、线路、设备、密码\n\n"
        "提示: 若功能不可用, 可能是权限不足或全局关闭。\n"
        "当总开关关闭时, 仅所有者可操作。\n\n"
        "请选择下方菜单开始使用 ⬇️"
    )
    image = get_common_image()
    kb = get_start_user_keyboard()
    if role == "admin":
        caption = (
            "🌸 桜色服务助手 | 管理员面板\n\n"
            "• 群组工具: 消息保存与导出\n"
            "• 管理功能: 权限配置与统计\n\n"
            "提示: 部分功能可能需所有者授权\n\n"
            "请选择下方菜单开始使用 ⬇️"
        )
        kb = get_start_admin_keyboard()
    elif role == "owner":
        caption = (
            "🌸 桜色服务助手 | 所有者控制台\n\n"
            "欢迎回来, 你拥有完整的管理权限:\n"
            "• 全局开关: 开启/关闭机器人\n"
            "• 管理与统计: 群组、数据统计、清理\n\n"
            "请选择下方菜单开始管理 ⬇️"
        )
        kb = get_start_owner_keyboard()
    msg = callback.message
    if isinstance(msg, types.Message):
        await render_view(msg, image, caption, kb)
    await callback.answer()
