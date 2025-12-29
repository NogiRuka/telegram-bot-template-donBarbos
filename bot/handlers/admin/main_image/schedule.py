from datetime import datetime as dt
from aiogram import F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.database.models import MainImageScheduleModel
from bot.keyboards.inline.admin import get_main_image_cancel_keyboard, get_main_image_back_keyboard
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.admin import AdminMainImageState
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2
from .router import router

@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule_list")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def list_schedules(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """查看节日投放列表
    
    功能说明:
    - 列出最近 10 条节日投放记录
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    result = await session.execute(
        select(MainImageScheduleModel).where(MainImageScheduleModel.is_deleted.is_(False)).order_by(MainImageScheduleModel.id.desc()).limit(10)
    )
    items = list(result.scalars().all())
    if not items:
        await main_msg.update_on_callback(callback, "暂无节日投放记录。", get_main_image_back_keyboard())
        await callback.answer()
        return
    lines = ["*📜 节日投放列表*"]
    for it in items:
        start_str = escape_markdown_v2(it.start_time.strftime('%Y-%m-%d %H:%M'))
        end_str = escape_markdown_v2(it.end_time.strftime('%Y-%m-%d %H:%M'))
        lines.append(
            fr"\- ID `{it.id}` \| image\_id\=`{it.image_id}` \| {start_str} \~ {end_str} \| priority\={it.priority}"
        )
    await main_msg.update_on_callback(callback, "\n".join(lines), get_main_image_back_keyboard())
    await callback.answer()


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_schedule(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始节日投放创建
    
    功能说明:
    - 展示当前已配置的投放列表
    - 引导依次输入 image_id、开始时间与结束时间
    
    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    # 展示现有投放
    text = (
        "请输入要投放的图片 ID:\n"
        "格式依次为：\n"
        r"1\. 图片ID" + "\n"
        r"2\. 开始时间 \(YYYY\-MM\-DD HH:MM\)" + "\n"
        r"3\. 结束时间 \(YYYY\-MM\-DD HH:MM\)"
    )
    await main_msg.update_on_callback(
        callback,
        text,
        get_main_image_cancel_keyboard()
    )
    await state.set_state(AdminMainImageState.waiting_for_schedule_image_id)
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_schedule_image_id)
async def process_schedule_image_id(message: Message, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理图片ID输入"""
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass
    try:
        image_id = int(message.text.strip())
    except Exception:
        await message.answer("❌ 请输入数字ID。")
        return
    await state.update_data(image_id=image_id)
    await state.set_state(AdminMainImageState.waiting_for_schedule_start)
    await message.answer("请输入开始时间 (YYYY-MM-DD HH:MM):")


@router.message(AdminMainImageState.waiting_for_schedule_start)
async def process_schedule_start(message: Message, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理开始时间输入"""
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass
    try:
        start_time = dt.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
    except Exception:
        await message.answer("❌ 时间格式错误，请按 YYYY-MM-DD HH:MM。")
        return
    await state.update_data(start_time=start_time)
    await state.set_state(AdminMainImageState.waiting_for_schedule_end)
    await message.answer("请输入结束时间 (YYYY-MM-DD HH:MM):")


@router.message(AdminMainImageState.waiting_for_schedule_end)
async def process_schedule_end(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理结束时间输入并创建投放"""
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass
    try:
        end_time = dt.strptime(message.text.strip(), "%Y-%m-%d %H:%M")
    except Exception:
        await message.answer("❌ 时间格式错误，请按 YYYY-MM-DD HH:MM。")
        return
    data = await state.get_data()
    image_id = int(data["image_id"])
    start_time = data["start_time"]
    model = MainImageScheduleModel(
        image_id=image_id,
        start_time=start_time,
        end_time=end_time,
        priority=0,
        only_sfw=False,
        allow_nsfw=True,
    )
    session.add(model)
    await session.commit()
    await state.clear()
    await main_msg.render(message.from_user.id, "✅ 已创建节日投放。", get_main_image_back_keyboard())


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule_delete")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_schedule_delete(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始删除投放
    
    功能说明:
    - 引导输入节日投放 ID 并删除记录
    
    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    
    返回值:
    - None
    """
    await state.set_state(AdminMainImageState.waiting_for_schedule_delete_id)
    await main_msg.update_on_callback(callback, "请输入要删除的投放 ID:", get_main_image_cancel_keyboard())
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_schedule_delete_id)
async def process_schedule_delete_id(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理删除投放 ID"""
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass
    try:
        schedule_id = int(message.text.strip())
    except Exception:
        await message.answer("❌ 请输入数字ID。")
        return
    try:
        await session.execute(delete(MainImageScheduleModel).where(MainImageScheduleModel.id == schedule_id))
        await session.commit()
        await main_msg.render(message.from_user.id, "✅ 已删除投放。", get_main_image_back_keyboard())
    except Exception:
        await message.answer("❌ 删除失败，请稍后重试。")
    await state.clear()
