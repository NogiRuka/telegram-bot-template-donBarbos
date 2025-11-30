from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.config_service import get_registration_window, is_registration_open
from bot.services.users import create_and_bind_emby_user
from bot.utils.text import safe_alert_text, safe_message_text

router = Router(name="user_register")


@router.callback_query(F.data == "user:register")
async def user_register(callback: CallbackQuery, session: AsyncSession) -> None:
    """开始注册

    功能说明:
    - 判断开放状态后创建 Emby 账号, 成功则告知用户名与密码

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
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
            text = (
                f"✅ 注册成功\n\nEmby 用户名: {details.get('name', '')}\nEmby 密码: {details.get('password', '')}\n"
            )
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

