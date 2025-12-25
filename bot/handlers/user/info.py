from aiogram import F, Router, types
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.emby_user import EmbyUserModel
from bot.keyboards.inline.constants import USER_INFO_LABEL
from bot.keyboards.inline.user import get_user_info_keyboard
from bot.services.main_message import MainMessageService
from bot.services.users import get_user_and_extend
from bot.utils.images import get_common_image
from bot.utils.permissions import require_user_feature
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
    # 查询用户账号信息
    user, ext = await get_user_and_extend(session, callback.from_user.id)

    # 查询 Emby 绑定信息
    emby_user = None
    if ext and ext.emby_user_id:
        res = await session.execute(select(EmbyUserModel).where(EmbyUserModel.emby_user_id == ext.emby_user_id))
        emby_user = res.scalar_one_or_none()

    # 构建 MarkdownV2 caption
    lines = [
        f"*{USER_INFO_LABEL}*",
        "",
    ]

    if emby_user:
        e_created = emby_user.date_created.strftime("%Y-%m-%d %H:%M:%S") if emby_user.date_created else "未知"
        e_last_login = emby_user.last_login_date.strftime("%Y-%m-%d %H:%M:%S") if emby_user.last_login_date else "从未登录"
        e_last_activity = emby_user.last_activity_date.strftime("%Y-%m-%d %H:%M:%S") if emby_user.last_activity_date else "从未活动"
        
        # 获取禁用状态
        is_disabled = False
        if emby_user.user_dto and isinstance(emby_user.user_dto, dict):
            policy = emby_user.user_dto.get("Policy", {})
            is_disabled = policy.get("IsDisabled", False)
        
        status_str = "🚫 已禁用" if is_disabled else "🟢 正常"

        lines.extend([
            f"🎬 Emby 账号：`{escape_markdown_v2(emby_user.name)}`",
            f"🆔 用户 ID：`{escape_markdown_v2(emby_user.emby_user_id)}`",
            f"📡 账号状态：{status_str}",
            f"📱 设备上限：{emby_user.max_devices} 台",
            f"🗓 创建时间：{escape_markdown_v2(e_created)}",
            f"🔐 最近登录：{escape_markdown_v2(e_last_login)}",
            f"🎥 最近活动：{escape_markdown_v2(e_last_activity)}",
        ])
    elif ext and ext.emby_user_id:
        lines.append(f"⚠️ 已绑定 ID: `{escape_markdown_v2(ext.emby_user_id)}`")
        lines.append("但尚未同步详细信息")
    else:
        lines.append("⚠️ 尚未绑定 Emby 账号")

    caption = "\n".join(lines)

    image = get_common_image()
    kb = get_user_info_keyboard()
    await main_msg.update_on_callback(callback, caption, kb, image)
