from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_NAME, CURRENCY_SYMBOL, DISPLAY_MODE_NSFW, DISPLAY_MODE_RANDOM, DISPLAY_MODE_SFW
from bot.keyboards.inline.constants import PROFILE_LABEL, PROFILE_MAIN_IMAGE_CALLBACK_DATA
from bot.keyboards.inline.user import get_main_image_settings_keyboard, get_user_profile_keyboard
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.services.users import get_user_and_extend
from bot.utils.permissions import require_user_feature
from bot.utils.text import escape_markdown_v2

router = Router(name="user_profile")


@router.callback_query(F.data == "user:profile")
@require_user_feature("user.profile")
async def user_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
    state: FSMContext,
) -> None:
    """个人信息

    功能说明:
    - 展示用户基本资料与状态
    - 不包含 Emby 绑定信息与扩展信息
    """
    await state.clear() # 清除可能存在的状态

    uid = callback.from_user.id if callback.from_user else None
    if not uid:
        await callback.answer("🔴 无法获取用户ID", show_alert=True)
        return

    # 查询用户账号信息
    user, ext = await get_user_and_extend(session, uid)

    # 获取货币余额
    balance = await CurrencyService.get_user_balance(session, uid)

    # 状态
    status_text = "正常" if (user and not getattr(user, "is_deleted", False)) else "已删除"

    # 字段整理
    first_name = getattr(user, "first_name", "")
    last_name = getattr(user, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip() or "未知"

    username = f"@{callback.from_user.username}" if callback.from_user and callback.from_user.username else "未设置"

    is_premium = getattr(user, "is_premium", False)
    premium_str = "是" if is_premium else "否"

    # 签到信息
    streak_days = getattr(ext, "streak_days", 0)
    max_streak_days = getattr(ext, "max_streak_days", 0)
    last_checkin = getattr(ext, "last_checkin_date", None)
    last_checkin_str = last_checkin.strftime("%Y-%m-%d") if last_checkin else "从未签到"

    # 构建 MarkdownV2 caption
    lines = [
        f"*{PROFILE_LABEL}*",
        "",
        "*基本信息*",
        f"🆔 用户ID：`{uid}`",
        f"📛 昵称：{escape_markdown_v2(full_name)}",
        f"🔗 用户名：{escape_markdown_v2(username)}",
        "",
        "*账户状态*",
        f"🌐 状态：{status_text}",
        f"💎 会员：{premium_str}",
        f"💰 {CURRENCY_NAME}：{balance} {CURRENCY_SYMBOL}",
        "",
        "*签到数据*",
        f"🔥 连签天数：{streak_days} 天",
        f"🏆 最高连签：{max_streak_days} 天",
        f"📝 上次签到：{escape_markdown_v2(last_checkin_str)}",
    ]

    caption = "\n".join(lines)

    kb = get_user_profile_keyboard()
    await main_msg.update_on_callback(callback, caption, kb)
    await callback.answer()


@router.callback_query(F.data == PROFILE_MAIN_IMAGE_CALLBACK_DATA)
@require_user_feature("user.profile")
async def main_image_settings(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """主图设置菜单"""
    uid = callback.from_user.id
    _, ext = await get_user_and_extend(session, uid)

    current_mode = ext.display_mode or DISPLAY_MODE_SFW
    nsfw_unlocked = ext.nsfw_unlocked

    text = (
        "🖼️ *主图设置*\n\n"
        "请选择您偏好的主图显示模式：\n\n"
        "• *SFW（安全）*：仅显示全年龄向内容\n"
        "• *NSFW（限制级）*：仅显示限制级内容（需解锁）\n"
        "• *随机（混合）*：混合显示所有内容（需解锁）\n"
    )

    kb = get_main_image_settings_keyboard(current_mode, nsfw_unlocked)
    await main_msg.update_on_callback(callback, text, kb)
    await callback.answer()


@router.callback_query(F.data.startswith(PROFILE_MAIN_IMAGE_CALLBACK_DATA + ":set:"))
@require_user_feature("user.profile")
async def set_main_image_mode(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """设置主图显示模式"""
    uid = callback.from_user.id
    _, ext = await get_user_and_extend(session, uid)

    target_mode = callback.data.split(":")[-1]

    # 验证权限
    if target_mode in (DISPLAY_MODE_NSFW, DISPLAY_MODE_RANDOM) and not ext.nsfw_unlocked:
        await callback.answer("🔒 您尚未解锁 NSFW 权限", show_alert=True)
        return

    if target_mode not in (DISPLAY_MODE_SFW, DISPLAY_MODE_NSFW, DISPLAY_MODE_RANDOM):
        await callback.answer("❌ 无效的模式", show_alert=True)
        return

    # 更新设置
    ext.display_mode = target_mode
    await session.commit()

    # 刷新界面
    await main_image_settings(callback, session, main_msg)
