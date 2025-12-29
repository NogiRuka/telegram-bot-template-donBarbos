from __future__ import annotations
from typing import Any
from datetime import datetime as dt

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED
from bot.database.models import MainImageModel, MainImageScheduleModel
from bot.keyboards.inline.admin import get_main_image_admin_keyboard
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService
from bot.services.main_image_service import MainImageService
from bot.states.admin import AdminMainImageState
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2

router = Router(name="admin_main_image")


@router.callback_query(F.data == "admin:main_image")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def show_main_image_panel(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """展示主图管理面板
    
    功能说明:
    - 显示主图管理的二级面板, 包含上传/列表/节日投放/测试/NSFW开关
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    enabled = bool(await get_config(session, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED) or False)
    text = (
        f"*🖼 主图管理*\n\n"
        f"当前 NSFW 开关: {'🟢 启用' if enabled else '🔴 禁用'}\n\n"
        f"请选择操作:"
    )
    await main_msg.update_on_callback(callback, text, get_main_image_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":toggle_nsfw")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def toggle_nsfw(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """切换 NSFW 全局开关
    
    功能说明:
    - 切换 admin.main_image.nsfw_enabled 配置项, 并刷新面板
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    current = bool(await get_config(session, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED) or False)
    await set_config(session, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED, (not current), config_type=None, operator_id=callback.from_user.id)
    await show_main_image_panel(callback, session, main_msg)


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_upload(callback: CallbackQuery, state: FSMContext) -> None:
    """开始上传流程
    
    功能说明:
    - 进入等待图片或文件消息的状态, 指引管理员发送照片或图片文档
    
    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    
    返回值:
    - None
    """
    await state.set_state(AdminMainImageState.waiting_for_image)
    await callback.message.edit_text(
        "请发送图片:\n- 支持 Photo(推荐, 自动记录宽高)\n- 支持 Document(图片文件)\n\n可附带说明作为 caption。",
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_image)
async def handle_image_upload(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理图片上传
    
    功能说明:
    - 接收管理员发送的 Photo 或 Document(图片)
    - 提取文件ID与基础元数据并写入 main_images 表
    
    输入参数:
    - message: 管理员消息
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass

    file_id: str | None = None
    source_type = "photo"
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    caption = message.caption or ""

    if message.photo:
        p = message.photo[-1]
        file_id = p.file_id
        width = p.width
        height = p.height
        file_size = p.file_size
        source_type = "photo"
    elif message.document:
        doc = message.document
        if doc.mime_type and doc.mime_type.startswith("image/"):
            file_id = doc.file_id
            mime_type = doc.mime_type
            file_size = doc.file_size
            source_type = "document"
        else:
            await message.answer("❌ 仅支持图片文档，请重试。")
            return
    else:
        await message.answer("❌ 未检测到图片，请发送 Photo 或 图片 Document。")
        return

    model = MainImageModel(
        file_id=file_id,
        source_type=source_type,
        mime_type=mime_type,
        width=width,
        height=height,
        file_size=file_size,
        is_nsfw=False,
        is_enabled=True,
        caption=caption or None,
    )
    session.add(model)
    await session.commit()

    text = (
        f"✅ 上传成功\n\n"
        f"ID: {model.id}\n"
        f"类型: {escape_markdown_v2(source_type)}\n"
        f"尺寸: {width or '-'} x {height or '-'}\n"
        f"大小: {escape_markdown_v2(str(file_size or 0))}B\n"
        f"NSFW: {'是' if model.is_nsfw else '否'}\n"
        f"启用: {'是' if model.is_enabled else '否'}\n"
    )
    await main_msg.update_by_message(message, text, get_main_image_admin_keyboard())
    await state.clear()

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
        await main_msg.update_on_callback(callback, "暂无节日投放记录。", get_main_image_admin_keyboard())
        await callback.answer()
        return
    lines = ["*📜 节日投放列表*"]
    for it in items:
        lines.append(
            f"- ID `{it.id}` | image_id={it.image_id} | {it.start_time:%Y-%m-%d %H:%M} ~ {it.end_time:%Y-%m-%d %H:%M} | priority={it.priority}"
        )
    await main_msg.update_on_callback(callback, "\n".join(lines), get_main_image_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":list")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def list_images(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """显示图片列表
    
    功能说明:
    - 列出最近 10 条图片并提供查看与操作入口
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    result = await session.execute(
        select(MainImageModel).where(MainImageModel.is_deleted.is_(False)).order_by(MainImageModel.id.desc()).limit(10)
    )
    items = list(result.scalars().all())
    if not items:
        await main_msg.update_on_callback(callback, "暂无图片，请先上传。", get_main_image_admin_keyboard())
        await callback.answer()
        return
    lines = ["*🗂 图片列表*"]
    for it in items:
        lines.append(
            f"- ID `{it.id}` | {'NSFW' if it.is_nsfw else 'SFW'} | {'启用' if it.is_enabled else '禁用'}"
        )
    lines.append("\n使用 /start 可在用户端验证展示效果。")
    await main_msg.update_on_callback(callback, "\n".join(lines), get_main_image_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    """开始节日投放创建
    
    功能说明:
    - 展示当前已配置的投放列表
    - 引导依次输入 image_id、开始时间与结束时间
    
    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    
    返回值:
    - None
    """
    # 展示现有投放
    try:
        # 读取数据库需要 session，但本函数没有注入；改由提示用户使用列表按钮查看
        await callback.message.edit_text(
            "请输入要投放的图片 ID:\n格式依次为：\n1) 图片ID\n2) 开始时间 (YYYY-MM-DD HH:MM)\n3) 结束时间 (YYYY-MM-DD HH:MM)",
            parse_mode="Markdown"
        )
    except Exception:
        pass
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
    await message.answer("✅ 已创建节日投放。")


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":schedule_delete")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_schedule_delete(callback: CallbackQuery, state: FSMContext) -> None:
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
    await callback.message.edit_text("请输入要删除的投放 ID:", parse_mode="Markdown")
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
        await message.answer("✅ 已删除投放。")
    except Exception:
        await message.answer("❌ 删除失败，请稍后重试。")
    await state.clear()


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":test")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_test(callback: CallbackQuery, state: FSMContext) -> None:
    """开始图片测试工具
    
    功能说明:
    - 引导输入 file_id 或发送图片进行信息回显
    
    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    
    返回值:
    - None
    """
    await state.set_state(AdminMainImageState.waiting_for_test_input)
    await callback.message.edit_text("请发送图片或直接输入 Telegram file_id：")
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_test_input)
async def process_test_input(message: Message, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理测试输入"""
    try:
        await main_msg.delete_input(message)
    except Exception:
        pass
    file_id: str | None = None
    caption_lines: list[str] = ["*🧪 图片测试结果*"]
    if message.photo:
        p = message.photo[-1]
        file_id = p.file_id
        caption_lines.extend([
            f"类型: Photo",
            f"尺寸: {p.width}x{p.height}",
            f"大小: {p.file_size}B",
        ])
    elif message.document:
        doc = message.document
        file_id = doc.file_id
        caption_lines.extend([
            f"类型: Document ({escape_markdown_v2(doc.mime_type or '-')})",
            f"大小: {doc.file_size}B",
        ])
    else:
        file_id = message.text.strip()
        caption_lines.append("类型: file_id")
    try:
        await message.bot.send_photo(chat_id=message.chat.id, photo=file_id, caption="\n".join(caption_lines), parse_mode="MarkdownV2")
    except Exception:
        await message.answer("❌ 发送失败，请确认 file_id 有效或重试。")
    await state.clear()
