from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import (
    KEY_ADMIN_QUIZ,
    KEY_QUIZ_COOLDOWN_MINUTES,
    KEY_QUIZ_DAILY_LIMIT,
    KEY_QUIZ_SCHEDULE_ENABLE,
    KEY_QUIZ_SCHEDULE_TARGET_COUNT,
    KEY_QUIZ_SCHEDULE_TARGET_TYPE,
    KEY_QUIZ_SCHEDULE_TIME,
    KEY_QUIZ_SESSION_TIMEOUT,
    KEY_QUIZ_TRIGGER_PROBABILITY,
)
from bot.database.models.config import ConfigType
from bot.keyboards.inline.admin import (
    get_quiz_schedule_keyboard,
    get_quiz_settings_selection_keyboard,
    get_quiz_trigger_keyboard,
)
from bot.keyboards.inline.constants import QUIZ_ADMIN_CALLBACK_DATA
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService
from bot.states.admin import QuizAdminState
from bot.utils.permissions import require_admin_feature


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":trigger")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_trigger_menu(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示问答触发设置主菜单"""
    # 获取概览信息
    prob = await get_config(session, KEY_QUIZ_TRIGGER_PROBABILITY)
    schedule_enabled = await get_config(session, KEY_QUIZ_SCHEDULE_ENABLE)
    schedule_time = await get_config(session, KEY_QUIZ_SCHEDULE_TIME)

    sch_status = "开启" if schedule_enabled else "关闭"
    sch_time_display = f"{schedule_time[:2]}:{schedule_time[2:4]}:{schedule_time[4:]}" if schedule_time and len(schedule_time) == 6 else "未设置"

    text = (
        "*⚙️ 触发设置*\n\n"
        f"当前状态概览：\n"
        f"• 随机触发概率：{prob:.1%}\n"
        f"• 定时触发状态：{sch_status}\n"
        f"• 定时触发时间：{sch_time_display}\n\n"
        "请选择要修改的设置项："
    ).replace(".", "\\.")
    
    await main_msg.update_on_callback(callback, text, get_quiz_trigger_keyboard())
    await callback.answer()


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":settings_menu")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_settings_menu(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示基础参数修改菜单"""
    prob = await get_config(session, KEY_QUIZ_TRIGGER_PROBABILITY)
    cooldown = await get_config(session, KEY_QUIZ_COOLDOWN_MINUTES)
    daily = await get_config(session, KEY_QUIZ_DAILY_LIMIT)
    timeout = await get_config(session, KEY_QUIZ_SESSION_TIMEOUT)

    text = (
        "*⚙️ 基础参数设置*\n\n"
        f"🎲 触发概率：{prob:.1%} \\(每次交互\\)\n"
        f"⏳ 冷却时间：{cooldown} 分钟\n"
        f"🔢 每日上限：{daily} 次\n"
        f"⏱️ 答题限时：{timeout} 秒"
    ).replace(".", "\\.")

    await main_msg.update_on_callback(callback, text, get_quiz_settings_selection_keyboard())
    await callback.answer()


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":schedule_menu")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def show_schedule_menu(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示定时触发设置菜单"""
    enabled = await get_config(session, KEY_QUIZ_SCHEDULE_ENABLE)
    time_str = await get_config(session, KEY_QUIZ_SCHEDULE_TIME)
    target_type = await get_config(session, KEY_QUIZ_SCHEDULE_TARGET_TYPE)
    target_count = await get_config(session, KEY_QUIZ_SCHEDULE_TARGET_COUNT)

    if enabled is None: enabled = False
    if not time_str: time_str = "未设置"
    else: time_str = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
    
    target_display = "全部用户"
    if target_type == "fixed":
        target_display = f"固定 {target_count} 人 (活跃+随机)"

    status_icon = "🟢" if enabled else "🔴"

    text = (
        "*⏰ 定时触发设置*\n\n"
        f"状态：{status_icon} {'开启' if enabled else '关闭'}\n"
        f"时间：{time_str}\n"
        f"对象：{target_display}\n\n"
        "说明：每天固定时间自动发送题目"
    )

    await main_msg.update_on_callback(callback, text, get_quiz_schedule_keyboard(is_enabled=enabled))
    await callback.answer()


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":set"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def ask_setting_value(callback: CallbackQuery, state: FSMContext) -> None:
    """请求输入设置值 (基础参数)"""
    setting_type = callback.data.split(":")[-1]
    await state.update_data(setting_type=setting_type)

    prompts = {
        "probability": "请输入新的触发概率 (0.0 - 1.0)，例如 0.05 表示 5%",
        "cooldown": "请输入新的冷却时间 (分钟，整数)",
        "daily_limit": "请输入新的每日触发上限 (整数)",
        "timeout": "请输入新的答题限时 (秒，整数)"
    }

    await callback.message.answer(prompts.get(setting_type, "请输入新值"))
    await state.set_state(QuizAdminState.waiting_for_setting_value)
    await callback.answer()


@router.callback_query(F.data.startswith(QUIZ_ADMIN_CALLBACK_DATA + ":schedule:set"))
@require_admin_feature(KEY_ADMIN_QUIZ)
async def ask_schedule_value(callback: CallbackQuery, state: FSMContext) -> None:
    """请求输入设置值 (定时参数)"""
    setting_type = callback.data.split(":")[-1] # set_time or set_target
    await state.update_data(setting_type=f"schedule_{setting_type}")

    if setting_type == "set_time":
        msg = (
            "⏰ 请设置每日定时触发时间\n"
            "格式：HHMMSS（6 位数字）\n"
            "多个时间请用英文逗号分隔，例如：\n"
            "`051700,171700,222222`"
        )
    elif setting_type == "set_target":
        msg = (
            "👥 请选择触发对象\n"
            "• 输入 `all` 或 `全部`：面向所有用户\n"
            "• 输入数字（如 `20`）：随机/活跃挑选 20 人"
        )
    else:
        msg = "请输入值"

    await callback.message.answer(msg)
    await state.set_state(QuizAdminState.waiting_for_setting_value)
    await callback.answer()


@router.callback_query(F.data == QUIZ_ADMIN_CALLBACK_DATA + ":schedule:toggle")
@require_admin_feature(KEY_ADMIN_QUIZ)
async def toggle_schedule(callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """切换定时任务开关"""
    current = await get_config(session, KEY_QUIZ_SCHEDULE_ENABLE)
    if current is None: current = False
    
    new_status = not current
    await set_config(session, KEY_QUIZ_SCHEDULE_ENABLE, new_status, ConfigType.BOOLEAN, operator_id=callback.from_user.id)
    await show_schedule_menu(callback, session, main_msg)


@router.message(QuizAdminState.waiting_for_setting_value)
@require_admin_feature(KEY_ADMIN_QUIZ)
async def process_setting_value(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """处理设置值输入 (统一处理基础和定时)"""
    data = await state.get_data()
    setting_type = data.get("setting_type")
    value_str = message.text.strip()
    user_id = message.from_user.id

    try:
        # 基础参数
        if setting_type == "probability":
            val = float(value_str)
            if not (0 <= val <= 1): raise ValueError
            await set_config(session, KEY_QUIZ_TRIGGER_PROBABILITY, val, ConfigType.FLOAT, operator_id=user_id)

        elif setting_type == "cooldown":
            val = int(value_str)
            await set_config(session, KEY_QUIZ_COOLDOWN_MINUTES, val, ConfigType.INTEGER, operator_id=user_id)

        elif setting_type == "daily_limit":
            val = int(value_str)
            await set_config(session, KEY_QUIZ_DAILY_LIMIT, val, ConfigType.INTEGER, operator_id=user_id)

        elif setting_type == "timeout":
            val = int(value_str)
            await set_config(session, KEY_QUIZ_SESSION_TIMEOUT, val, ConfigType.INTEGER, operator_id=user_id)
        
        # 定时参数
        elif setting_type == "schedule_set_time":
            # 支持多个时间，逗号分隔
            time_parts = [t.strip() for t in value_str.split(",") if t.strip()]
            if not time_parts:
                await message.answer("⚠️ 请输入有效的时间")
                return

            for part in time_parts:
                if len(part) != 6 or not part.isdigit():
                    await message.answer(f"⚠️ 格式错误: {part}，请输入 6 位数字，如 222222")
                    return
                # 简单的校验
                h, m, s = int(part[:2]), int(part[2:4]), int(part[4:])
                if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
                    await message.answer(f"⚠️ 时间数值不合法: {part}")
                    return
            
            # 保存处理后的字符串(去空格)
            final_value = ",".join(time_parts)
            await set_config(session, KEY_QUIZ_SCHEDULE_TIME, final_value, ConfigType.STRING, operator_id=user_id)

        elif setting_type == "schedule_set_target":
            if value_str.lower() == "all" or value_str == "全部":
                await set_config(session, KEY_QUIZ_SCHEDULE_TARGET_TYPE, "all", ConfigType.STRING, operator_id=user_id)
            elif value_str.isdigit():
                count = int(value_str)
                if count <= 0: raise ValueError
                await set_config(session, KEY_QUIZ_SCHEDULE_TARGET_TYPE, "fixed", ConfigType.STRING, operator_id=user_id)
                await set_config(session, KEY_QUIZ_SCHEDULE_TARGET_COUNT, count, ConfigType.INTEGER, operator_id=user_id)
            else:
                await message.answer("⚠️ 输入无效，请输入 'all' 或正整数")
                return

        await message.answer("✅ 设置已更新！")
        await state.clear()

    except ValueError:
        await message.answer("⚠️ 输入无效，请重试。")
    except Exception as e:
        await message.answer(f"❌ 设置失败: {e}")
