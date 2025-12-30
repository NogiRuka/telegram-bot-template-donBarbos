from math import ceil

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="admin_files")
from bot.config.constants import KEY_ADMIN_FILES
from bot.database.models import MediaFileModel
from bot.keyboards.inline.admin import (
    get_files_admin_keyboard,
    get_files_list_pagination_keyboard,
    get_main_image_cancel_keyboard,
)
from bot.keyboards.inline.constants import FILE_ADMIN_CALLBACK_DATA, FILE_ADMIN_LABEL
from bot.services.main_message import MainMessageService
from bot.states.admin import AdminFileState
from bot.utils.message import send_toast
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2, format_size


@router.callback_query(F.data == FILE_ADMIN_CALLBACK_DATA)
@require_admin_feature(KEY_ADMIN_FILES)
async def show_files_panel(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """展示文件管理面板

    功能说明:
    - 显示文件管理入口，包括保存文件与查看文件

    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    await state.clear()
    text = (
        f"*{FILE_ADMIN_LABEL}*\n\n"
        "支持接收图片、文档、视频、音频、语音、动画等文件类型并保存基础信息。\n"
        "查看文件时仅对 photo 类型发送媒体预览，其他类型只展示信息。\n\n"
        "请在下方选择操作："
    )
    await main_msg.update_on_callback(callback, text, get_files_admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == FILE_ADMIN_CALLBACK_DATA + ":save")
@require_admin_feature(KEY_ADMIN_FILES)
async def start_file_save(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始保存文件流程

    功能说明:
    - 设置状态等待用户发送文件（或图片等）
    - 提供取消按钮

    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    await state.set_state(AdminFileState.waiting_for_file_input)
    await main_msg.update_on_callback(
        callback,
        "请发送要保存的文件（支持图片、文档、视频、音频、语音、动画等）",
        get_main_image_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminFileState.waiting_for_file_input)
async def handle_file_input(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理文件输入并保存

    功能说明:
    - 识别消息中的文件类型，提取基础元数据并保存到数据库
    - 成功后返回保存结果摘要

    输入参数:
    - message: 用户消息
    - session: 数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    media_type = None
    file_id = None
    file_unique_id = None
    file_size = None
    file_name = None
    mime_type = None
    width = None
    height = None
    duration = None

    try:
        if message.photo:
            p = message.photo[-1]
            media_type = "photo"
            file_id = p.file_id
            file_unique_id = getattr(p, "file_unique_id", None)
            file_size = getattr(p, "file_size", None)
            width = getattr(p, "width", None)
            height = getattr(p, "height", None)
        elif message.document:
            d = message.document
            media_type = "document"
            file_id = d.file_id
            file_unique_id = getattr(d, "file_unique_id", None)
            file_size = getattr(d, "file_size", None)
            file_name = getattr(d, "file_name", None)
            mime_type = getattr(d, "mime_type", None)
        elif message.video:
            v = message.video
            media_type = "video"
            file_id = v.file_id
            file_unique_id = getattr(v, "file_unique_id", None)
            file_size = getattr(v, "file_size", None)
            width = getattr(v, "width", None)
            height = getattr(v, "height", None)
            duration = getattr(v, "duration", None)
            mime_type = getattr(v, "mime_type", None)
        elif message.audio:
            a = message.audio
            media_type = "audio"
            file_id = a.file_id
            file_unique_id = getattr(a, "file_unique_id", None)
            file_size = getattr(a, "file_size", None)
            duration = getattr(a, "duration", None)
            mime_type = getattr(a, "mime_type", None)
            file_name = getattr(a, "file_name", None)
        elif message.voice:
            v = message.voice
            media_type = "voice"
            file_id = v.file_id
            file_unique_id = getattr(v, "file_unique_id", None)
            file_size = getattr(v, "file_size", None)
            duration = getattr(v, "duration", None)
            mime_type = getattr(v, "mime_type", None)
        elif message.animation:
            an = message.animation
            media_type = "animation"
            file_id = an.file_id
            file_unique_id = getattr(an, "file_unique_id", None)
            file_size = getattr(an, "file_size", None)
            width = getattr(an, "width", None)
            height = getattr(an, "height", None)
            duration = getattr(an, "duration", None)
            mime_type = getattr(an, "mime_type", None)
        elif message.sticker:
            s = message.sticker
            media_type = "sticker"
            file_id = s.file_id
            file_unique_id = getattr(s, "file_unique_id", None)
            file_size = getattr(s, "file_size", None)
            width = getattr(s, "width", None)
            height = getattr(s, "height", None)
            # sticker 没有 mime_type 与文件名
        elif message.video_note:
            vn = message.video_note
            media_type = "video_note"
            file_id = vn.file_id
            file_unique_id = getattr(vn, "file_unique_id", None)
            file_size = getattr(vn, "file_size", None)
            duration = getattr(vn, "duration", None)
            width = getattr(vn, "length", None)
            height = getattr(vn, "length", None)
        else:
            await message.answer("⚠️ 未检测到支持的文件类型或该消息不包含文件内容")
            return

        model = MediaFileModel(
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_size=file_size,
            file_name=file_name,
            mime_type=mime_type,
            media_type=media_type,
            width=width,
            height=height,
            duration=duration,
            created_by=message.from_user.id if message.from_user else None,
            updated_by=message.from_user.id if message.from_user else None,
        )
        session.add(model)
        await session.commit()

        size_str = escape_markdown_v2(format_size(file_size or 0))
        mime_str = escape_markdown_v2(mime_type or "-")
        name_str = escape_markdown_v2(file_name or "-")
        summary = (
            "*✅ 文件已保存*\n"
            f"类型: {escape_markdown_v2(media_type)}\n"
            f"大小: {size_str}\n"
            f"MIME: {mime_str}\n"
            f"文件名: {name_str}\n"
            f"ID: `{model.id}`"
        )
        await main_msg.render(message.from_user.id, summary)
    except Exception as e:
        logger.exception("保存文件失败")
        await message.answer(f"❌ 保存失败: {e}")
    finally:
        await state.clear()


@router.callback_query(F.data.startswith(FILE_ADMIN_CALLBACK_DATA + ":list"))
@require_admin_feature(KEY_ADMIN_FILES)
async def list_files(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """查看文件列表（分页）

    功能说明:
    - 分页展示已保存的文件记录
    - photo 类型发送媒体预览，其他类型仅发送信息

    输入参数:
    - callback: 回调对象
    - session: 数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    try:
        parts = callback.data.split(":")
        page = int(parts[3]) if len(parts) >= 4 else 1
        limit = int(parts[4]) if len(parts) >= 5 else 10
    except ValueError:
        await callback.answer("❌ 参数错误", show_alert=True)
        return

    count_stmt = select(func.count()).where(MediaFileModel.is_deleted.is_(False))
    total_count = (await session.execute(count_stmt)).scalar_one()
    total_pages = ceil(total_count / limit) if total_count > 0 else 1
    page = max(page, 1)
    page = min(page, total_pages)

    stmt = (
        select(MediaFileModel)
        .where(MediaFileModel.is_deleted.is_(False))
        .order_by(MediaFileModel.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = (await session.execute(stmt)).scalars().all()

    header = f"*📜 文件列表*\n共 {total_count} 条，当前第 {page}/{total_pages} 页"
    await main_msg.update_on_callback(callback, header, get_files_list_pagination_keyboard(page, total_pages, limit))

    if not items:
        await send_toast(callback, "暂无数据")
        return

    for it in items:
        size_str = escape_markdown_v2(format_size(it.file_size or 0))
        mime_str = escape_markdown_v2(it.mime_type or "-")
        name_str = escape_markdown_v2(it.file_name or "-")
        caption = (
            f"🆔 `{it.id}` ｜ 类型: {escape_markdown_v2(it.media_type)} ｜ "
            f"MIME: {mime_str} ｜ 📦 {size_str} ｜ 文件名: {name_str}"
        )
        try:
            if it.media_type == "photo":
                await callback.message.answer_photo(photo=it.file_id, caption=caption, parse_mode="MarkdownV2")
            else:
                await callback.message.answer(caption, parse_mode="MarkdownV2")
        except Exception as e:
            await callback.message.answer(f"❌ 文件 ID `{it.id}` 发送失败: {e}")
    await callback.answer()
