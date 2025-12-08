import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.start_user import (
    get_account_center_keyboard,
    get_register_input_keyboard,
)
from bot.services.config_service import get_registration_window, is_registration_open
from bot.services.main_message import MainMessageService
from bot.services.users import create_and_bind_emby_user, has_emby_account
from bot.utils.text import safe_alert_text

router = Router(name="user_register")

# 注册超时时间（秒）
REGISTER_TIMEOUT_SECONDS = 120


class RegisterStates(StatesGroup):
    """注册状态组"""

    waiting_for_credentials = State()


@router.callback_query(F.data == "user:register")
async def user_register(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService
) -> None:
    """开始注册

    功能说明:
    - 判断开放状态后进入注册流程
    - 修改主消息提示用户输入用户名和密码
    - 设置 FSM 状态等待用户输入

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    uid = callback.from_user.id if callback.from_user else None
    start = None
    dur = None

    logger.info("用户开始注册: user_id={}", uid)
    try:
        if not await is_registration_open(session):
            window = await get_registration_window(session) or {}
            hint = "🚫 暂未开放注册"
            start = window.get("start_iso")
            dur = window.get("duration_minutes")
            
            if start and dur:
                hint += f"\n开始: {start}\n时长: {dur} 分钟"
            elif start:
                hint += f"\n开始: {start}"
            elif dur:
                hint += f"\n时长: {dur} 分钟"
            return await callback.answer(safe_alert_text(hint), show_alert=True)

        if not uid:
            return await callback.answer("🔴 无法获取用户ID", show_alert=True)

        if await has_emby_account(session, uid):
            return await callback.answer("ℹ️ 您已绑定 Emby 账号", show_alert=True)

        # 更新主消息提示输入
        caption = (
            "📝 注册 Emby 账号\n\n"
            "请输入用户名和密码，以空格分隔：\n"
            "用户名 密码\n\n"
            "示例：myuser mypassword123\n\n"
            f"⏰ 请在 {REGISTER_TIMEOUT_SECONDS // 60} 分钟内完成输入"
        )

        await main_msg.update_on_callback(callback, caption, get_register_input_keyboard())

        # 设置 FSM 状态
        await state.set_state(RegisterStates.waiting_for_credentials)
        await callback.answer()

        # 启动超时任务
        asyncio.create_task(_register_timeout(state, uid, main_msg, REGISTER_TIMEOUT_SECONDS))

    except TelegramAPIError as e:
        logger.exception(f"❌ 注册流程 TelegramAPIError: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)
    except Exception as e:
        logger.exception(f"❌ 注册流程未知异常: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)


async def _register_timeout(
    state: FSMContext, user_id: int, main_msg: MainMessageService, timeout: int
) -> None:
    """注册超时处理

    功能说明:
    - 等待指定时间后检查状态，如果仍在等待输入则自动取消

    输入参数:
    - state: FSM 上下文
    - user_id: 用户 ID
    - main_msg: 主消息服务
    - timeout: 超时秒数

    返回值:
    - None
    """
    await asyncio.sleep(timeout)

    current_state = await state.get_state()
    if current_state == RegisterStates.waiting_for_credentials.state:
        await state.clear()
        caption = "⏰ 注册超时，请重新开始"
        await main_msg.update(user_id, caption, get_account_center_keyboard(has_emby_account=False))
        logger.info("⏰ 注册超时，已自动取消: user_id={}", user_id)


@router.callback_query(F.data == "user:cancel_register")
async def cancel_register(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService
) -> None:
    """取消注册

    功能说明:
    - 用户点击取消按钮时清除状态并返回账号中心

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    uid = callback.from_user.id if callback.from_user else None
    try:
        await state.clear()

        if uid:
            user_has_emby = await has_emby_account(session, uid)
            await main_msg.update_on_callback(callback, "🧩 账号中心", get_account_center_keyboard(user_has_emby))

        await callback.answer("✅ 已取消注册")
        logger.info("ℹ️ 用户取消注册: user_id={}", uid)

    except Exception as e:
        logger.exception(f"❌ 取消注册异常: {e!r}")
        await callback.answer("🔴 操作失败", show_alert=True)


@router.message(RegisterStates.waiting_for_credentials)
async def handle_register_input(
    message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService
) -> None:
    """处理用户输入的用户名和密码

    功能说明:
    - 解析用户输入，创建 Emby 账号
    - 删除用户消息，更新主消息显示结果

    输入参数:
    - message: 用户消息
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    uid = message.from_user.id if message.from_user else None

    # 删除用户输入消息
    await main_msg.delete_input(message)

    if not uid:
        await state.clear()
        return

    try:
        text = (message.text or "").strip()
        parts = text.split(maxsplit=1)

        if len(parts) != 2:
            caption = "❌ 格式错误\n\n请输入用户名和密码，以空格分隔：\n用户名 密码\n\n示例：myuser mypassword123"
            await main_msg.update(uid, caption, get_register_input_keyboard())
            return

        name, password = parts[0], parts[1]

        # 验证用户名和密码
        if len(name) < 2:
            caption = "❌ 用户名至少需要 2 个字符\n\n请重新输入用户名和密码，以空格分隔：\n用户名 密码"
            await main_msg.update(uid, caption, get_register_input_keyboard())
            return
        if len(password) < 6:
            caption = "❌ 密码至少需要 6 个字符\n\n请重新输入用户名和密码，以空格分隔：\n用户名 密码"
            await main_msg.update(uid, caption, get_register_input_keyboard())
            return

        # 创建用户
        ok, details, err = await create_and_bind_emby_user(session, uid, name, password)
        
        if ok and details:
            await state.clear()
            caption = (
                f"✅ 注册成功\n\n"
                f"📛 Emby 用户名: {details.get('name', '')}\n"
                f"🔑 Emby 密码: {details.get('password', '')}\n\n"
                f"请妥善保管您的账号信息"
            )
            await main_msg.update(uid, caption, get_account_center_keyboard(has_emby_account=True))
        else:
            err_msg = err or "未知错误"
            if "already exists" in err_msg or "already exist" in err_msg:
                # 不清除状态，允许用户重新输入
                caption = (
                    f"❌ 用户名 '{name}' 已存在\n\n"
                    f"请更换一个用户名重试：\n"
                    f"新用户名 密码"
                )
                await main_msg.update(uid, caption, get_register_input_keyboard())
            else:
                await state.clear()
                caption = f"❌ 注册失败\n\n{err_msg}"
                await main_msg.update(uid, caption, get_account_center_keyboard(has_emby_account=False))

    except Exception as e:
        logger.exception(f"❌ 处理注册输入异常: user_id={uid} err={e!r}")
        await state.clear()
