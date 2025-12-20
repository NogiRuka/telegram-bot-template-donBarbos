from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.emby_user import EmbyUserModel
from bot.keyboards.inline.user import get_user_info_keyboard
from bot.services.main_message import MainMessageService
from bot.services.users import get_user_and_extend
from bot.utils.images import get_common_image
from bot.utils.permissions import _resolve_role, require_user_feature
from bot.utils.text import escape_markdown_v2

router = Router(name="user_info")


@router.callback_query(F.data == "user:info")
@require_user_feature("user.info")
async def user_info(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService,
) -> None:
    """账号信息

    功能说明:
    - 在 caption 上展示账号信息
    - 包含 Emby 绑定状态与扩展信息

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

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

    # 查询用户账号信息
    user, ext = await get_user_and_extend(session, uid)

    # 查询 Emby 绑定信息
    emby_info = "未绑定"
    if ext and ext.emby_user_id:
        res = await session.execute(select(EmbyUserModel).where(EmbyUserModel.emby_user_id == ext.emby_user_id))
        emby_user = res.scalar_one_or_none()
        if emby_user:
            emby_info = escape_markdown_v2(emby_user.name)
        else:
            emby_info = f"已绑定但未同步 \\(ID: `{escape_markdown_v2(ext.emby_user_id)}`\\)"

    # 角色与状态
    role = ext.role.value if ext and ext.role else "user"  # 直接使用 ext 中的角色信息
    status_text = "正常" if (user and not getattr(user, "is_deleted", False)) else "已删除"

    # 字段整理
    first_name = getattr(user, "first_name", "")
    last_name = getattr(user, "last_name", "") or ""
    full_name = f"{first_name} {last_name}".strip() or "未知"
    
    username = f"@{callback.from_user.username}" if callback.from_user and callback.from_user.username else "未设置"
    language = getattr(user, "language_code", "zh-hans") or "zh-hans"
    
    created_at = getattr(user, "created_at", None)
    created_str = created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "未知"
    
    is_premium = getattr(user, "is_premium", None)
    premium_str = "是" if is_premium else ("否" if is_premium is not None else "未知")
    
    last_interaction = getattr(ext, "last_interaction_at", None)
    last_interaction_str = last_interaction.strftime("%Y-%m-%d %H:%M:%S") if last_interaction else "未知"

    # 构建 MarkdownV2 caption
    lines = [
        "👤 *个人信息中心*",
        "",
        "*基本资料*",
        f"🆔 用户ID: `{uid}`",
        f"📛 昵称: {escape_markdown_v2(full_name)}",
        f"🔗 用户名: {escape_markdown_v2(username)}",
        f"🌐 语言: {escape_markdown_v2(language)}",
        "",
        "*账户状态*",
        f"🛡 角色: {role.value if hasattr(role, 'value') else str(role)}",
        f"📡 状态: {status_text}",
        f"💎 Premium: {premium_str}",
        f"📅 注册时间: {escape_markdown_v2(created_str)}",
        f"⏱ 最后活跃: {escape_markdown_v2(last_interaction_str)}",
        "",
        "*Emby 绑定*",
        f"🎬 账号: {emby_info}",
    ]

    caption = "\n".join(lines)

    image = get_common_image()
    kb = get_user_info_keyboard()
    await main_msg.update_on_callback(callback, caption, kb, image)
    await callback.answer()
