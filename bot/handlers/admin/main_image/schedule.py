from math import ceil
from datetime import datetime as dt, timedelta as td
import re

from aiogram import F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.database.models import MainImageScheduleModel, MainImageModel
from bot.keyboards.inline.admin import (
    get_main_image_schedule_menu_keyboard,
    get_main_image_schedule_list_pagination_keyboard,
    get_main_image_schedule_item_keyboard,
    get_main_image_schedule_cancel_keyboard,
)
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.admin import AdminMainImageState
from bot.utils.permissions import require_admin_feature
from bot.utils.message import send_toast, safe_delete_message
from bot.utils.text import escape_markdown_v2
from bot.utils.datetime import now
from bot.handlers.start import build_home_view
from .router import router


async def _clear_schedule_list(state: FSMContext, bot: Bot, chat_id: int) -> None:
    """清理已发送的投放列表消息"""
    data = await state.get_data()
    msg_ids = data.get("main_image_schedule_list_ids", [])
    if not msg_ids:
        return

    for msg_id in msg_ids:
        await safe_delete_message(bot, chat_id, msg_id)
    
    await state.update_data(main_image_schedule_list_ids=[])


def _parse_schedule_input(text: str) -> tuple[list[int], dt, dt, str | None] | None:
    """解析投放输入
    格式支持:
    - 1.202512010021.202512012359 [Label] (ID.Start.End [Label])
    - 1-2-3.20251201 [Label] (IDs.StartDay [Label])
    - 1.202512010021 [Label] (ID.Start, End=StartDayEnd or NextDay00:00 [Label])
    - 1.20251201 [Label] (ID.StartDay, End=NextDay00:00 [Label])
    - 1.20251201.20251205 [Label] (ID.StartDay.EndDay [Label])
    - 1.20251201-05 [Label] (ID.StartDay-EndDaySuffix [Label])
    """
    try:
        # 分离标签 (空格分隔)
        parts_with_label = text.strip().split(maxsplit=1)
        schedule_text = parts_with_label[0]
        label = parts_with_label[1] if len(parts_with_label) > 1 else None

        parts = schedule_text.split('.', 1)
        if len(parts) != 2:
            return None
        
        # 解析 ID 部分 (支持单个或连字符分隔)
        id_part = parts[0]
        image_ids = []
        try:
            for x in id_part.split('-'):
                if x.strip():
                    image_ids.append(int(x.strip()))
        except ValueError:
            return None
            
        if not image_ids:
            return None

        date_part = parts[1]
        
        start_dt = None
        end_dt = None
        
        # 模式1: 包含 - (1.20251201-05)
        if '-' in date_part:
            start_str, end_suffix = date_part.split('-')
            if len(start_str) != 8:
                return None
            start_dt = dt.strptime(start_str, "%Y%m%d")
            # 结束日期为 start_dt 的年月 + end_suffix
            end_day = int(end_suffix)
            # 构造结束日期: 年月取自 start_dt, 日取自 end_suffix
            # 结束时间应该是那一天的结束，或者下一天的0点。通常 1-5号 包含5号，所以是 6号0点
            target_end_date = start_dt.replace(day=end_day) + td(days=1)
            end_dt = target_end_date
            
        # 模式2: 包含 . (1.20251201.20251205 或 1.202512010021.202512012359)
        elif '.' in date_part:
            start_str, end_str = date_part.split('.')
            # 判断精度
            if len(start_str) == 12: # YYYYMMDDHHMM
                start_dt = dt.strptime(start_str, "%Y%m%d%H%M")
            elif len(start_str) == 8: # YYYYMMDD
                start_dt = dt.strptime(start_str, "%Y%m%d")
            else:
                return None
                
            if len(end_str) == 12:
                end_dt = dt.strptime(end_str, "%Y%m%d%H%M")
            elif len(end_str) == 8:
                # 结束日期包含当天，所以 +1 天
                end_dt = dt.strptime(end_str, "%Y%m%d") + td(days=1)
            else:
                return None
                
        # 模式3: 单个时间/日期 (1.20251201 或 1.202512010021)
        else:
            if len(date_part) == 12:
                start_dt = dt.strptime(date_part, "%Y%m%d%H%M")
                # 默认为当天结束 (下一天0点)
                end_dt = (start_dt + td(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            elif len(date_part) == 8:
                start_dt = dt.strptime(date_part, "%Y%m%d")
                end_dt = start_dt + td(days=1)
            else:
                return None
                
        return image_ids, start_dt, end_dt, label
    except Exception:
        return None


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def schedule_menu(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """节日投放菜单"""
    # 清理可能存在的列表
    if callback.message:
        await _clear_schedule_list(state, callback.bot, callback.message.chat.id)
        
    text = "🗓️ *节日投放管理*\n\n请选择操作："
    await main_msg.update_on_callback(callback, text, get_main_image_schedule_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule:create")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_schedule_creation(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始创建投放"""
    now_dt = now()
    day_str = now_dt.strftime('%Y%m%d')
    next_day_str = (now_dt + td(days=1)).strftime('%Y%m%d')
    range_end_str = (now_dt + td(days=4)).strftime('%Y%m%d')
    # 对于简写范围，如果跨月可能显示不直观，这里简单处理，如果+4天还在同一个月，就显示 DD，否则显示下个月的 DD
    # 但逻辑上 1.20251201-05 是同一个月。
    # 为了演示方便，我们假设用户会在当月操作。如果今天是月底，例子可能看起来像 1.20251230-03 (这是无效的逻辑吗？_parse_schedule_input 里 replace(day=3) 会变成当月3号，即过去时间)
    # 所以为了避免混淆，简写范围例子最好固定或者确保有效。
    # 既然用户要求 "根据now来"，我们尽量动态生成。如果 now_dt.day > 25，我们就在例子中用下个月1号开始。
    
    example_base_dt = now_dt
    if example_base_dt.day > 25:
        # 下个月1号
        if example_base_dt.month == 12:
            example_base_dt = example_base_dt.replace(year=example_base_dt.year + 1, month=1, day=1)
        else:
            example_base_dt = example_base_dt.replace(month=example_base_dt.month + 1, day=1)
    
    example_day_str = example_base_dt.strftime('%Y%m%d')
    example_suffix = (example_base_dt + td(days=4)).strftime('%d')
    
    text = (
        "➕ *创建节日投放*\n\n"
        "请按以下格式输入（支持多种格式）：\n"
        "`ID.开始时间[.结束时间] [标签]`\n\n"
        "📝 *示例*：\n"
        f"1\\. 精确时间段：`1.{day_str}0021.{day_str}2359 元旦活动`\n"
        f"2\\. 当天剩余时间：`1.{day_str}0021`\n"
        f"3\\. 全天：`1.{day_str} 周末`\n"
        f"4\\. 日期范围：`1.{day_str}.{range_end_str}`\n"
        f"5\\. 简写范围：`1.{example_day_str}-{example_suffix}`"
    )
    await main_msg.update_on_callback(callback, text, get_main_image_schedule_cancel_keyboard())
    await state.set_state(AdminMainImageState.waiting_for_schedule_input)
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_schedule_input)
async def process_schedule_input(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理投放输入"""
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass
        
    result = _parse_schedule_input(message.text)
    if not result:
        await message.answer("❌ 格式错误，请检查输入格式。")
        return
        
    image_ids, start_time, end_time, label = result
    
    # 验证图片是否存在
    valid_ids = []
    invalid_ids = []
    
    for image_id in image_ids:
        image = await session.get(MainImageModel, image_id)
        if image:
            valid_ids.append(image_id)
        else:
            invalid_ids.append(image_id)
            
    if not valid_ids:
        await message.answer(f"❌ 所有图片 ID 均不存在。")
        return

    # 创建投放记录
    for image_id in valid_ids:
        model = MainImageScheduleModel(
            image_id=image_id,
            start_time=start_time,
            end_time=end_time,
            priority=0, # 默认优先级
            only_sfw=False,
            allow_nsfw=True,
            label=label
        )
        session.add(model)
        
    await session.commit()
    
    await state.clear()
    
    valid_ids_str = ", ".join(map(str, valid_ids))
    label_info = f"\n🏷️ 标签: `{escape_markdown_v2(label)}`" if label else ""
    info = (
        f"✅ *投放创建成功*\n"
        f"🆔 图片: `{valid_ids_str}`\n"
        f"📅 开始: `{start_time.strftime('%Y-%m-%d %H:%M')}`\n"
        f"📅 结束: `{end_time.strftime('%Y-%m-%d %H:%M')}`"
        f"{label_info}"
    )
    
    if invalid_ids:
        invalid_ids_str = ", ".join(map(str, invalid_ids))
        info += f"\n⚠️ 未找到ID: `{invalid_ids_str}`"
    
    await main_msg.render(message.from_user.id, info, get_main_image_schedule_menu_keyboard())


@router.callback_query(F.data.startswith(MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule:list"))
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def list_schedules(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService, state: FSMContext) -> None:
    """查看节日投放列表（分页）"""
    # 解析参数: admin:main_image:schedule:list:1:5
    try:
        parts = callback.data.split(":")
        page = int(parts[4])
        limit = int(parts[5])
    except (IndexError, ValueError):
        # 容错处理
        page = 1
        limit = 5

    # 清理旧消息
    if callback.message:
        await _clear_schedule_list(state, callback.bot, callback.message.chat.id)
        
    # 查询总数
    count_stmt = select(func.count()).where(MainImageScheduleModel.is_deleted.is_(False))
    total_count = (await session.execute(count_stmt)).scalar_one()
    total_pages = ceil(total_count / limit) if total_count > 0 else 1
    
    if page > total_pages: page = total_pages
    if page < 1: page = 1
    
    # 查询数据
    stmt = (
        select(MainImageScheduleModel, MainImageModel)
        .join(MainImageModel, MainImageScheduleModel.image_id == MainImageModel.id)
        .where(MainImageScheduleModel.is_deleted.is_(False))
        .order_by(MainImageScheduleModel.start_time.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    
    # 更新主控消息
    text = (
        f"*🗓️ 节日投放列表*\n"
        f"共 {total_count} 条，当前第 {page}/{total_pages} 页"
    )
    await main_msg.update_on_callback(
        callback, 
        text, 
        get_main_image_schedule_list_pagination_keyboard(page, total_pages, limit)
    )
    
    if not rows:
        await send_toast(callback, "暂无数据")
        return
        
    new_msg_ids = []
    for item, image in rows:
        now_time = now()
        if item.start_time > now_time:
            status_emoji = "🕒"
            status_text = "未开始"
        elif item.end_time < now_time:
            status_emoji = "⛔"
            status_text = "已结束"
        else:
            status_emoji = "🟢"
            status_text = "投放中"
        start_str = escape_markdown_v2(item.start_time.strftime('%Y-%m-%d %H:%M'))
        end_str = escape_markdown_v2(item.end_time.strftime('%Y-%m-%d %H:%M'))
        label_suffix = f" · 🏷️ {escape_markdown_v2(item.label)}" if item.label else ""
        
        caption = (
            f"{status_emoji} *节日投放 · {status_text}{label_suffix}*\n\n"
            f"🖼️ *图片ID*：`{item.image_id}`\n"
            f"⏰ *投放时间*：\n"
            f"　{start_str} \\~ {end_str}\n"
        )
        
        try:
            kwargs = {
                "caption": caption,
                "reply_markup": get_main_image_schedule_item_keyboard(item.id),
                "parse_mode": "MarkdownV2"
            }
            
            msg = None
            if image.source_type == "document":
                msg = await callback.message.answer_document(document=image.file_id, **kwargs)
            else:
                msg = await callback.message.answer_photo(photo=image.file_id, **kwargs)
                
            if msg:
                new_msg_ids.append(msg.message_id)
        except Exception as e:
            await callback.message.answer(f"❌ 投放 ID `{item.id}` 加载失败: {e}")
            
    await state.update_data(main_image_schedule_list_ids=new_msg_ids)
    await callback.answer()


@router.callback_query(F.data.startswith(MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule:item:"))
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def schedule_item_action(callback: CallbackQuery, session: AsyncSession) -> None:
    """投放条目操作"""
    try:
        parts = callback.data.split(":")
        action = parts[4]
        
        if action == "close":
            await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
            return
            
        schedule_id = int(parts[5])
    except (IndexError, ValueError):
        await callback.answer("❌ 参数错误", show_alert=True)
        return
        
    if action == "delete":
        item = await session.get(MainImageScheduleModel, schedule_id)
        if item:
            item.is_deleted = True
            item.deleted_at = now()
            item.deleted_by = callback.from_user.id
            item.remark = f"由 {callback.from_user.full_name}（ID：{callback.from_user.id}）手动删除"

            # 级联禁用关联的图片
            image = await session.get(MainImageModel, item.image_id)
            if image:
                image.is_enabled = False
                image.updated_by = callback.from_user.id
                image.remark = f"随投放计划 {item.id} 删除而被禁用"

            await session.commit()
            await send_toast(callback, "✅ 投放已删除")
            await safe_delete_message(callback.bot, callback.message.chat.id, callback.message.message_id)
        else: 
            await callback.answer("❌ 记录不存在", show_alert=True)


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule:back_home")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def back_to_home_from_schedule_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """返回主面板"""
    if callback.message:
        await _clear_schedule_list(state, callback.bot, callback.message.chat.id)
        
    uid = callback.from_user.id if callback.from_user else None
    caption, kb = await build_home_view(session, uid)
    
    await main_msg.update_on_callback(callback, caption, kb)
    await callback.answer()
