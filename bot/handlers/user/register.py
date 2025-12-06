import asyncio

from aiogram import F, Router, types
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.config_service import get_registration_window, is_registration_open
from bot.services.users import create_and_bind_emby_user, has_emby_account
from bot.utils.text import safe_alert_text, safe_message_text

router = Router(name="user_register")

# 注册超时时间（秒）
REGISTER_TIMEOUT_SECONDS = 120


class RegisterStates(StatesGroup):
    """注册状态组"""

    waiting_for_credentials = State()


def get_cancel_register_keyboard() -> types.InlineKeyboardMarkup:
    """获取取消注册键盘

    功能说明:
    - 返回带有取消注册按钮的键盘

    输入参数:
    - 无

    返回值:
    - InlineKeyboardMarkup: 取消注册键盘
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ 取消注册", callback_data="user:cancel_register")
    return builder.as_markup()


@router.callback_query(F.data == "user:register")
async def user_register(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """开始注册

    功能说明:
    - 判断开放状态后进入注册流程
    - 修改消息提示用户输入用户名和密码
    - 设置 FSM 状态等待用户输入

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - state: FSM 上下文

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

        # 检查是否已绑定
        if await has_emby_account(session, uid):
            return await callback.answer("ℹ️ 您已绑定 Emby 账号", show_alert=True)

        msg = callback.message
        if not isinstance(msg, types.Message):
            return await callback.answer("🔴 消息对象异常", show_alert=True)

        # 修改消息提示用户输入
        caption = (
            "📝 <b>注册 Emby 账号</b>\n\n"
            "请输入用户名和密码，以空格分隔：\n"
            "<code>用户名 密码</code>\n\n"
            "示例：<code>myuser mypassword123</code>\n\n"
            f"⏰ 请在 {REGISTER_TIMEOUT_SECONDS // 60} 分钟内完成输入"
        )
        await msg.edit_caption(caption=caption, reply_markup=get_cancel_register_keyboard(), parse_mode="HTML")

        # 设置 FSM 状态
        await state.set_state(RegisterStates.waiting_for_credentials)
        await state.update_data(message_id=msg.message_id, chat_id=msg.chat.id)

        await callback.answer()

        # 启动超时任务
        asyncio.create_task(_register_timeout(state, msg, REGISTER_TIMEOUT_SECONDS))

    except TelegramAPIError as e:
        uid = callback.from_user.id if callback.from_user else None
        logger.exception(f"❌ 注册流程 TelegramAPIError: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)
    except Exception as e:
        uid = callback.from_user.id if callback.from_user else None
        logger.exception(f"❌ 注册流程未知异常: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)


async def _register_timeout(state: FSMContext, msg: types.Message, timeout: int) -> None:
    """注册超时处理

    功能说明:
    - 等待指定时间后检查状态，如果仍在等待输入则自动取消

    输入参数:
    - state: FSM 上下文
    - msg: 原消息对象，用于恢复
    - timeout: 超时秒数

    返回值:
    - None
    """
    await asyncio.sleep(timeout)

    current_state = await state.get_state()
    if current_state == RegisterStates.waiting_for_credentials.state:
        await state.clear()
        try:
            # 恢复原消息
            from bot.handlers.start import build_home_view

            caption, keyboard = await build_home_view(None, msg.chat.id)
            await msg.edit_caption(caption=caption, reply_markup=keyboard)
            logger.info("⏰ 注册超时，已自动取消: chat_id={}", msg.chat.id)
        except Exception as e:
            logger.warning("⚠️ 恢复消息失败: {}", str(e))


@router.callback_query(F.data == "user:cancel_register")
async def cancel_register(callback: CallbackQuery, state: FSMContext) -> None:
    """取消注册

    功能说明:
    - 用户点击取消按钮时清除状态并恢复原消息

    输入参数:
    - callback: 回调对象
    - state: FSM 上下文

    返回值:
    - None
    """
    try:
        await state.clear()

        msg = callback.message
        if isinstance(msg, types.Message):
            from bot.handlers.start import build_home_view

            caption, keyboard = await build_home_view(None, msg.chat.id)
            await msg.edit_caption(caption=caption, reply_markup=keyboard)

        await callback.answer("✅ 已取消注册")
        logger.info("ℹ️ 用户取消注册: user_id={}", callback.from_user.id if callback.from_user else None)

    except Exception as e:
        logger.exception(f"❌ 取消注册异常: {e!r}")
        await callback.answer("🔴 操作失败", show_alert=True)


@router.message(RegisterStates.waiting_for_credentials)
async def handle_register_input(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """处理用户输入的用户名和密码

    功能说明:
    - 解析用户输入，创建 Emby 账号
    - 删除用户消息，更新主消息显示结果

    输入参数:
    - message: 用户消息
    - session: 异步数据库会话
    - state: FSM 上下文

    返回值:
    - None
    """
    uid = message.from_user.id if message.from_user else None

    # 删除用户消息
    try:
        await message.delete()
    except Exception:
        pass

    try:
        text = (message.text or "").strip()
        parts = text.split(maxsplit=1)

        if len(parts) != 2:
            # 输入格式错误，提示用户重新输入
            data = await state.get_data()
            msg_id = data.get("message_id")
            chat_id = data.get("chat_id")
            if msg_id and chat_id:
                error_caption = (
                    "❌ <b>格式错误</b>\n\n"
                    "请输入用户名和密码，以空格分隔：\n"
                    "<code>用户名 密码</code>\n\n"
                    "示例：<code>myuser mypassword123</code>"
                )
                try:
                    await message.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=msg_id,
                        caption=error_caption,
                        reply_markup=get_cancel_register_keyboard(),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            return

        name, password = parts[0], parts[1]

        # 验证用户名和密码
        if len(name) < 2:
            await _show_error(message, state, "用户名至少需要 2 个字符")
            return
        if len(password) < 6:
            await _show_error(message, state, "密码至少需要 6 个字符")
            return

        # 创建用户
        ok, details, err = await create_and_bind_emby_user(session, uid, name, password)

        data = await state.get_data()
        msg_id = data.get("message_id")
        chat_id = data.get("chat_id")

        await state.clear()

        if msg_id and chat_id:
            if ok and details:
                success_caption = (
                    f"✅ <b>注册成功</b>\n\n"
                    f"📛 Emby 用户名: <code>{details.get('name', '')}</code>\n"
                    f"🔑 Emby 密码: <code>{details.get('password', '')}</code>\n\n"
                    f"请妥善保管您的账号信息"
                )
                try:
                    from bot.keyboards.inline.start_user import get_account_center_keyboard

                    await message.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=msg_id,
                        caption=success_caption,
                        reply_markup=get_account_center_keyboard(has_emby_account=True),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning("⚠️ 更新消息失败: {}", str(e))
            else:
                error_caption = f"❌ <b>注册失败</b>\n\n{err or '未知错误'}"
                try:
                    from bot.keyboards.inline.start_user import get_account_center_keyboard

                    await message.bot.edit_message_caption(
                        chat_id=chat_id,
                        message_id=msg_id,
                        caption=error_caption,
                        reply_markup=get_account_center_keyboard(has_emby_account=False),
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.warning("⚠️ 更新消息失败: {}", str(e))

    except Exception as e:
        logger.exception(f"❌ 处理注册输入异常: user_id={uid} err={e!r}")
        await state.clear()


async def _show_error(message: Message, state: FSMContext, error: str) -> None:
    """显示错误消息

    功能说明:
    - 在主消息中显示错误提示

    输入参数:
    - message: 用户消息对象
    - state: FSM 上下文
    - error: 错误信息

    返回值:
    - None
    """
    data = await state.get_data()
    msg_id = data.get("message_id")
    chat_id = data.get("chat_id")
    if msg_id and chat_id:
        error_caption = (
            f"❌ <b>{error}</b>\n\n"
            "请重新输入用户名和密码，以空格分隔：\n"
            "<code>用户名 密码</code>"
        )
        try:
            await message.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=msg_id,
                caption=error_caption,
                reply_markup=get_cancel_register_keyboard(),
                parse_mode="HTML",
            )
        except Exception:
            pass

