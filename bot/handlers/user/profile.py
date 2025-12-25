from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_NAME, CURRENCY_SYMBOL
from bot.keyboards.inline.constants import PROFILE_LABEL
from bot.keyboards.inline.user import get_user_profile_keyboard
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.services.users import get_user_and_extend
from bot.utils.images import get_common_image
from bot.utils.permissions import require_user_feature
from bot.utils.text import escape_markdown_v2

router = Router(name="user_profile")


@router.callback_query(F.data == "user:profile")
@require_user_feature("user.profile")
async def user_profile(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """个人信息

    功能说明:
    - 展示用户基本资料与状态
    - 不包含 Emby 绑定信息与扩展信息

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """

    uid = callback.from_user.id if callback.from_user else None
    if not uid:
        await callback.answer("🔴 无法获取用户ID", show_alert=True)
        return

    # 查询用户账号信息
    user, ext = await get_user_and_extend(session, uid)
    
    # 获取货币余额
    balance = await CurrencyService.get_user_balance(session, uid)

    # 角色与状态
    role_map = {
        "user": "普通用户",
        "admin": "管理员",
        "owner": "所有者"
    }
    role_val = getattr(ext, "role", "user")
    role_str = role_val.value if hasattr(role_val, "value") else str(role_val)
    role_display = role_map.get(role_str, role_str)
    
    status_text = "正常" if (user and not getattr(user, "is_deleted", False)) else "已删除"

    # 字段整理
    first_name = getattr(user, "first_name", "")
    last_name = getattr(user, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip() or "未知"

    username = f"@{callback.from_user.username}" if callback.from_user and callback.from_user.username else "未设置"

    created_at = getattr(user, "created_at", None)
    created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "未知"

    is_premium = getattr(user, "is_premium", False)
    premium_str = "是" if is_premium else "否"

    last_interaction = getattr(ext, "last_interaction_at", None)
    last_interaction_str = last_interaction.strftime("%Y-%m-%d %H:%M:%S") if last_interaction else "未知"

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
        f"🆔 用户ID: `{uid}`",
        f"📛 昵称: {escape_markdown_v2(full_name)}",
        f"🔗 用户名: {escape_markdown_v2(username)}",
        "",
        "*账户状态*",
        f"🛡 角色: {role_display}",
        f"📡 状态: {status_text}",
        f"💎 Premium: {premium_str}",
        f"💰 {CURRENCY_NAME}: {balance} {CURRENCY_SYMBOL}",
        "",
        "*签到数据*",
        f"🔥 连签天数: {streak_days} 天",
        f"🏆 最高连签: {max_streak_days} 天",
        f"📝 上次签到: {escape_markdown_v2(last_checkin_str)}",
        "",
        "*系统信息*",
        f"📅 注册时间: {escape_markdown_v2(created_str)}",
        f"⏱ 最后活跃: {escape_markdown_v2(last_interaction_str)}",
    ]

    caption = "\n".join(lines)

    image = get_common_image()
    kb = get_user_profile_keyboard()
    await main_msg.update_on_callback(callback, caption, kb, image)
    await callback.answer()
