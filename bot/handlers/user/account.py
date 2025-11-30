from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.start import get_common_image
from bot.keyboards.inline.labels import BACK_LABEL, BACK_TO_HOME_LABEL
from bot.keyboards.inline.start_user import get_account_center_keyboard
from bot.services.config_service import get_registration_window, is_registration_open
from bot.services.users import create_and_bind_emby_user
from bot.utils.permissions import _resolve_role, require_user_feature
from bot.utils.text import escape_markdown_v2, safe_alert_text, safe_message_text
from bot.utils.view import render_view

router = Router(name="user_account")


@router.callback_query(F.data == "user:account")
async def show_account_center(callback: CallbackQuery, session: AsyncSession) -> None:
    """展示账号中心

    功能说明:
    - 展示二级账号中心菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    uid = callback.from_user.id if callback.from_user else None
    has_emby_account = False
    try:
        if uid:
            has_emby_account = await has_emby_account(session, uid)
    except Exception:
        has_emby_account = False

    kb = get_account_center_keyboard(has_emby_account)
    msg = callback.message
    if isinstance(msg, types.Message):
        await _resolve_role(session, uid)
        image = get_common_image()
        await render_view(msg, image, "🧩 账号中心", kb)
    await callback.answer()


@router.callback_query(F.data == "user:register")
@require_user_feature("user.register")
async def user_register(callback: CallbackQuery, session: AsyncSession) -> None:
    """开始注册"""
    try:
        if not await is_registration_open(session):
            window = await get_registration_window(session) or {}
            hint = "🚫 暂未开放注册"
            if (start := window.get("start_iso")) and (dur := window.get("duration_minutes")):
                hint += f"\n开始: {start}\n时长: {dur} 分钟"
            elif start:
                hint += f"\n开始: {start}"
            elif dur:
                hint += f"\n时长: {dur} 分钟"
            return await callback.answer(safe_alert_text(hint), show_alert=True)

        if not (uid := callback.from_user.id if callback.from_user else None):
            return await callback.answer("🔴 无法获取用户ID", show_alert=True)

        base_name = (
            callback.from_user.username
            or callback.from_user.first_name
            or callback.from_user.last_name
            or None
        )
        ok, details, err = await create_and_bind_emby_user(session, uid, base_name)
        if not ok:
            return await callback.answer(safe_alert_text(f"❌ {err or '注册失败'}"), show_alert=True)

        if isinstance(msg := callback.message, types.Message) and details:
            text = f"✅ 注册成功\n\nEmby 用户名: {details.get('name', '')}\nEmby 密码: {details.get('password', '')}\n"
            await msg.answer(safe_message_text(text))
        await callback.answer("✅ 已为您创建 Emby 账号", show_alert=False)

    except TelegramAPIError as e:
        uid = callback.from_user.id if callback.from_user else None
        logger.exception(f"注册流程 TelegramAPIError: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)
    except Exception as e:
        uid = callback.from_user.id if callback.from_user else None
        logger.exception(f"注册流程未知异常: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)


@router.callback_query(F.data == "user:info")
@require_user_feature("user.info")
async def user_info(callback: CallbackQuery, session: AsyncSession) -> None:
    """账号信息

    功能说明:
    - 在 caption 上展示账号信息

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    msg = callback.message
    if not isinstance(msg, types.Message):
        await callback.answer("🔴 无法获取消息对象", show_alert=True)
        return

    uid = callback.from_user.id if callback.from_user else None
    if not uid:
        await callback.answer("🔴 无法获取用户ID", show_alert=True)
        return

    from bot.services.users import get_user_and_extend

    # 查询用户账号信息
    user, ext = await get_user_and_extend(session, uid)

    # 角色与状态
    role = await _resolve_role(session, uid)
    status_text = "正常" if (user and not getattr(user, "is_deleted", False)) else "已删除"

    # 字段整理
    username = f"@{callback.from_user.username}" if callback.from_user and callback.from_user.username else "未设置"
    username_md = escape_markdown_v2(username)
    created_at = getattr(user, "created_at", None)
    created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "未知"
    is_premium = getattr(user, "is_premium", None)
    premium_str = "是" if is_premium else ("否" if is_premium is not None else "未知")
    last_interaction = getattr(ext, "last_interaction_at", None)
    last_interaction_str = last_interaction.strftime("%Y-%m-%d %H:%M:%S") if last_interaction else "未知"
    phone = getattr(ext, "phone", None) or "未设置"
    bio = getattr(ext, "bio", None) or "未设置"

    # 构建 MarkdownV2 caption
    caption = (
        "👤 账号信息\n"
        f"├ 用户ID: `{uid}`\n"
        f"├ 用户名: {username_md}\n"
        f"├ 角色: {role}\n"
        f"├ 注册时间: {created_str}\n"
        f"├ 最后交互: {last_interaction_str}\n"
        f"├ Premium: {premium_str}\n"
        f"├ 电话: {escape_markdown_v2(phone)}\n"
        f"├ 简介: {escape_markdown_v2(bio)}\n"
        f"└ 状态: {status_text}"
    )

    image = get_common_image()
    buttons = [
        [
            InlineKeyboardButton(text=BACK_LABEL, callback_data="user:account"),
            InlineKeyboardButton(text=BACK_TO_HOME_LABEL, callback_data="home:back"),
        ]
    ]
    kb = InlineKeyboardBuilder(markup=buttons).as_markup()
    await render_view(msg, image, caption, kb)
    await callback.answer()


@router.callback_query(F.data == "user:lines")
@require_user_feature("user.lines")
async def user_lines(callback: CallbackQuery, session: AsyncSession) -> None:
    """线路信息

    功能说明:
    - 展示线路信息入口, 当前为占位实现

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    if session is None:
        pass
    try:
        await callback.answer("功能建设中, 请稍后再试", show_alert=True)
    except TelegramAPIError:
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)


@router.callback_query(F.data == "user:devices")
@require_user_feature("user.devices")
async def user_devices(callback: CallbackQuery, session: AsyncSession) -> None:
    """设备管理

    功能说明:
    - 进入设备管理入口, 当前为占位实现

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    if session is None:
        pass
    try:
        await callback.answer("功能建设中, 请稍后再试", show_alert=True)
    except TelegramAPIError:
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)


@router.callback_query(F.data == "user:password")
@require_user_feature("user.password")
async def user_password(callback: CallbackQuery, session: AsyncSession) -> None:
    """修改密码

    功能说明:
    - 进入修改密码入口, 当前为占位实现

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    if session is None:
        pass
    try:
        await callback.answer("功能建设中, 请稍后再试", show_alert=True)
    except TelegramAPIError:
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)


@router.callback_query(F.data == "user:profile")
async def user_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    """个人信息

    功能说明:
    - 展示个人信息入口, 当前为占位实现

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    if session is None:
        pass
    try:
        await callback.answer("功能建设中, 请稍后再试", show_alert=True)
    except TelegramAPIError:
        await callback.answer("❌ 系统异常, 请稍后再试", show_alert=True)
