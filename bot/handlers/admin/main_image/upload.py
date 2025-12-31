import contextlib
from io import BytesIO

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .router import router
from bot.config.constants import KEY_ADMIN_MAIN_IMAGE
from bot.database.models import MainImageModel
from bot.keyboards.inline.admin import (
    get_main_image_cancel_keyboard,
    get_main_image_upload_success_keyboard,
    get_main_image_upload_type_keyboard,
)
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.main_message import MainMessageService
from bot.states.admin import AdminMainImageState
from bot.utils.images import get_image_dimensions
from bot.utils.message import send_toast
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2, format_size


@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload")
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_upload_selection(callback: CallbackQuery, main_msg: MainMessageService) -> None:
    """开始上传流程 - 选择类型

    功能说明:
    - 显示 SFW/NSFW 选择键盘
    """
    text = "请选择上传图片的类型:"
    await main_msg.update_on_callback(
        callback,
        text,
        get_main_image_upload_type_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.in_([
    MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload:sfw",
    MAIN_IMAGE_ADMIN_CALLBACK_DATA + ":upload:nsfw"
]))
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def start_upload_process(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """进入具体类型的上传状态"""
    is_nsfw = callback.data.endswith(":nsfw")
    await state.set_state(AdminMainImageState.waiting_for_image)
    await state.update_data(is_nsfw=is_nsfw)

    type_text = "NSFW" if is_nsfw else "SFW"
    text = (
        f"📤 请发送 *{escape_markdown_v2(type_text)}* 类型图片：\n\n"
        "📸 支持格式：\n"
        r"• Photo \(推荐，自动记录宽高\)" + "\n"
        r"• Document \(图片文件\)" + "\n\n"
        "💬 可附带说明作为 caption。"
    )

    await main_msg.update_on_callback(
        callback,
        text,
        get_main_image_cancel_keyboard()
    )
    await callback.answer()


@router.message(AdminMainImageState.waiting_for_image)
async def handle_image_upload(message: Message, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """处理图片上传"""
    # 随机延迟以缓解并发竞争
    if message.media_group_id and not message.caption:
         # 无 Caption 的消息稍微多等一下
         pass
    
    with contextlib.suppress(Exception):
        await main_msg.delete_input(message)

    file_id: str | None = None
    source_type = "photo"
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    caption = message.caption

    # 处理媒体组(相册)共享 Caption
    if message.media_group_id:
        group_key = f"media_group_caption_{message.media_group_id}"
        
        if caption:
            # 当前消息有 Caption，保存到状态供同组其他消息使用
            await state.update_data({group_key: caption})
        else:
            # 当前消息无 Caption，稍作等待以确保带 Caption 的消息已写入状态
            await asyncio.sleep(1.0)
            # 尝试从状态获取
            data = await state.get_data()
            caption = data.get(group_key, "")
    
    caption = caption or ""

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

            # 尝试下载图片并读取尺寸
            try:
                io_obj = BytesIO()
                await message.bot.download(doc, destination=io_obj)
                dims = get_image_dimensions(io_obj)
                if dims:
                    width, height = dims
            except Exception:
                # 忽略读取尺寸失败，允许 width/height 为 None
                pass
        else:
            await message.answer("❌ 仅支持图片文档，请重试。")
            return
    else:
        await message.answer("❌ 未检测到图片，请发送 Photo 或 图片 Document。")
        return

    # 重复检测: 相同 file_id 不允许重复上传
    try:
        exists_stmt = select(MainImageModel.id).where(MainImageModel.file_id == file_id)
        exists = await session.execute(exists_stmt)
        if exists.scalar_one_or_none() is not None:
            await send_toast(message, "❌ 图片重复了，请重新上传")
            return
    except Exception:
        # 忽略检测失败，后续还有唯一约束保护
        pass

    # 获取当前上传类型
    data = await state.get_data()
    is_nsfw = data.get("is_nsfw", False)

    model = MainImageModel(
        file_id=file_id,
        source_type=source_type,
        mime_type=mime_type,
        width=width,
        height=height,
        file_size=file_size,
        caption=caption,
        is_nsfw=is_nsfw,  # 使用状态中的设置
    )
    session.add(model)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        await send_toast(message, "❌ 图片重复了，请重新上传")
        return

    safe_caption = escape_markdown_v2(caption)
    text = (
        "🎉 *上传成功啦～* 🌸\n\n"
        f"🆔 *ID*：`{model.id}`\n"
        f"🖼 *规格*：{escape_markdown_v2(f'{width} × {height}')} ｜ "
        f"{escape_markdown_v2(format_size(file_size))}\n"
        f"{'🔞 NSFW' if model.is_nsfw else '🌿 SFW'} ｜ "
        f"{'🟢 启用中' if model.is_enabled else '🔴 已禁用'}"
    )
    if caption:
        text += f"\n📝 {safe_caption}"
    
    text += "\n\n📸 *请继续发送图片，或点击下方按钮结束上传*"

    # 保持状态不清除，允许连续上传
    # await state.clear()
    
    # 使用 Cancel 键盘 (点击返回主菜单并清除状态)
    await main_msg.render(message.from_user.id, text, get_main_image_cancel_keyboard())
