import asyncio

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline.user import get_account_center_keyboard, get_password_input_keyboard
from bot.core.constants import CURRENCY_SYMBOL
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.services.users import get_user_and_extend
from bot.utils.permissions import require_emby_account, require_user_feature
from bot.utils.security import hash_password

router = Router(name="user_password")

# 修改密码超时时间（秒）
PASSWORD_TIMEOUT_SECONDS = 120
# 修改密码消耗精粹
PASSWORD_CHANGE_COST = 60


class PasswordStates(StatesGroup):
    """修改密码状态组"""

    waiting_for_new_password = State()


@router.callback_query(F.data == "user:password")
@require_user_feature("user.password")
@require_emby_account
async def user_password(callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """修改密码

    功能说明:
    - 进入修改密码流程
    - 检查用户是否已绑定 Emby 账号
    - 修改主消息提示用户输入新密码
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
    if not uid:
        return await callback.answer("🔴 无法获取用户ID", show_alert=True)

    try:
        # 获取用户扩展信息 (require_emby_account 已保证存在)
        _user, user_extend = await get_user_and_extend(session, uid)
        
        # 检查余额
        balance = await CurrencyService.get_user_balance(session, uid)
        if balance < PASSWORD_CHANGE_COST:
            return await callback.answer(
                f"🔴 余额不足，修改密码需要 {PASSWORD_CHANGE_COST} {CURRENCY_SYMBOL}\n"
                f"当前余额: {balance} {CURRENCY_SYMBOL}", 
                show_alert=True
            )

        logger.info("用户开始修改密码: user_id={} emby_user_id={}", uid, user_extend.emby_user_id)

        # 更新主消息提示输入新密码
        caption = (
            "🔐 *修改 Emby 密码*\n\n"
            f"本次修改将消耗 *{PASSWORD_CHANGE_COST} {CURRENCY_SYMBOL}*\n"
            f"当前余额: {balance} {CURRENCY_SYMBOL}\n\n"
            "请输入新的密码：\n"
            "密码长度至少需要 6 个字符\n\n"
            f"⏰ 请在 {PASSWORD_TIMEOUT_SECONDS // 60} 分钟内完成输入"
        )

        await main_msg.update_on_callback(callback, caption, get_password_input_keyboard())

        # 设置 FSM 状态
        await state.set_state(PasswordStates.waiting_for_new_password)
        await state.update_data(emby_user_id=user_extend.emby_user_id)
        await callback.answer()

        # 启动超时任务
        asyncio.create_task(_password_timeout(state, uid, main_msg, PASSWORD_TIMEOUT_SECONDS))

    except TelegramAPIError as e:
        logger.exception(f"❌ 修改密码流程 TelegramAPIError: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)
    except Exception as e:
        logger.exception(f"❌ 修改密码流程未知异常: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)


async def _password_timeout(state: FSMContext, uid: int, main_msg: MainMessageService, timeout: int) -> None:
    """修改密码超时处理

    功能说明:
    - 超时后清理 FSM 状态并返回账号中心

    输入参数:
    - state: FSM 上下文
    - uid: 用户ID
    - main_msg: 主消息服务
    - timeout: 超时时间（秒）

    返回值:
    - None
    """
    await asyncio.sleep(timeout)
    current_state = await state.get_state()
    if current_state == PasswordStates.waiting_for_new_password:
        logger.info("用户修改密码超时: user_id={}", uid)
        await state.clear()
        await main_msg.render(
            uid,
            "⏰ 修改密码超时，已自动返回账号中心",
            get_account_center_keyboard(uid)
        )


@router.message(PasswordStates.waiting_for_new_password)
async def handle_new_password(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理用户输入的新密码

    功能说明:
    - 验证密码长度
    - 更新 Emby 用户密码
    - 更新数据库中的密码哈希
    - 返回账号中心

    输入参数:
    - message: 消息对象
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    uid = message.from_user.id if message.from_user else None
    if not uid:
        return None

    try:
        # 获取用户输入的密码
        new_password = message.text.strip() if message.text else ""

        # 验证密码长度
        if len(new_password) < 6:
            await message.delete()
            return await main_msg.render(
                uid,
                "🔴 密码长度至少需要 6 个字符，请重新输入：",
                get_password_input_keyboard()
            )

        # 获取状态数据
        data = await state.get_data()
        emby_user_id = data.get("emby_user_id")
        data.get("old_password_hash")

        if not emby_user_id:
            await state.clear()
            return await main_msg.render(
                uid,
                "🔴 状态异常，请重新尝试",
                get_account_center_keyboard(uid)
            )

        logger.info("用户提交新密码: user_id={} emby_user_id={}", uid, emby_user_id)

        # 删除用户消息
        await message.delete()

        # 1. 预扣除代币 (不立即提交，等待 Emby 操作成功)
        try:
            await CurrencyService.add_currency(
                session,
                uid,
                -PASSWORD_CHANGE_COST,
                "password_change",
                "修改 Emby 密码",
                commit=False
            )
        except ValueError:
            # 余额不足 (理论上入口处已拦截，但防止并发或状态变化)
            await state.clear()
            return await main_msg.render(
                uid,
                f"🔴 余额不足，修改密码需要 {PASSWORD_CHANGE_COST} {CURRENCY_SYMBOL}",
                get_account_center_keyboard(uid)
            )

        # 2. 更新 Emby 用户密码
        from bot.utils.emby import get_emby_client

        client = get_emby_client()
        if not client:
            await state.clear()
            return await main_msg.render(
                uid,
                "🔴 Emby 服务配置异常，请联系管理员",
                get_account_center_keyboard(uid)
            )
        
        # 调用 Emby API
        await client.update_user_password(emby_user_id, new_password)

        # 3. 更新数据库中的密码哈希
        new_password_hash = hash_password(new_password)
        from sqlalchemy import select

        from bot.database.models import EmbyUserHistoryModel, EmbyUserModel

        result = await session.execute(select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id))
        emby_user = result.scalar_one_or_none()
        if emby_user:
            logger.info(f"🔍 找到用户，准备更新密码和历史记录: id={emby_user.id} emby_id={emby_user_id}")
            # 先保存历史记录（保存修改前的旧数据）
            history = EmbyUserHistoryModel(
                emby_user_id=emby_user_id,
                name=emby_user.name,
                user_dto=emby_user.user_dto,
                password_hash=emby_user.password_hash,  # 保存旧的密码哈希
                date_created=emby_user.date_created,
                last_login_date=emby_user.last_login_date,
                last_activity_date=emby_user.last_activity_date,
                action="update",
                # 保存原记录的审计信息（快照）
                created_at=emby_user.created_at,
                updated_at=emby_user.updated_at,
                created_by=emby_user.created_by,
                updated_by=emby_user.updated_by,
                is_deleted=emby_user.is_deleted,
                deleted_at=emby_user.deleted_at,
                deleted_by=emby_user.deleted_by,
                remark=emby_user.remark,
            )
            session.add(history)

            # 再更新用户表为新密码哈希
            emby_user.password_hash = new_password_hash
            emby_user.updated_by = uid  # 更新操作者
            emby_user.remark = "用户修改密码"  # 更新备注
            session.add(emby_user)
        else:
            logger.warning(f"⚠️ 未在数据库中找到用户 {emby_user_id}，仅更新了 Emby 端密码")

        # 4. 提交事务 (包含扣款和数据库更新)
        await session.commit()

        # 清理 FSM 状态
        await state.clear()

        # 返回账号中心
        await main_msg.render(
            uid,
            "✅ 密码修改成功！已返回账号中心",
            get_account_center_keyboard(uid)
        )

        logger.info("用户密码修改成功: user_id={} emby_user_id={}", uid, emby_user_id)

    except TelegramAPIError as e:
        logger.exception(f"❌ 处理密码输入 TelegramAPIError: user_id={uid} err={e!r}")
        await state.clear()
        await main_msg.render(
            uid,
            "🔴 系统异常, 请稍后再试",
            get_account_center_keyboard(uid)
        )


@router.callback_query(F.data == "user:cancel_password")
@require_user_feature("user.password")
async def cancel_password_change(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """取消修改密码

    功能说明:
    - 取消当前的密码修改流程
    - 清理 FSM 状态
    - 返回账号中心

    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    uid = callback.from_user.id if callback.from_user else None
    if not uid:
        return await callback.answer("🔴 无法获取用户ID", show_alert=True)

    try:
        # 清理 FSM 状态
        await state.clear()

        # 返回账号中心
        await main_msg.update_on_callback(
            callback,
            "✅ 已取消修改密码，已返回账号中心",
            get_account_center_keyboard(uid)
        )

        logger.info("用户取消修改密码: user_id={}", uid)

    except TelegramAPIError as e:
        logger.exception(f"❌ 取消修改密码 TelegramAPIError: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)
    except Exception as e:
        logger.exception(f"❌ 取消修改密码未知异常: user_id={uid} err={e!r}")
        await callback.answer("🔴 系统异常, 请稍后再试", show_alert=True)

