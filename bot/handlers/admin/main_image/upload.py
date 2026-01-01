import asyncio
from typing import List

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
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
from bot.utils.message import send_toast
from bot.utils.permissions import require_admin_feature
from bot.utils.text import escape_markdown_v2, format_size
from loguru import logger


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
async def handle_image_upload(
    message: Message, 
    session: AsyncSession, 
    state: FSMContext, 
    main_msg: MainMessageService,
    album: List[Message] = None  # 由 AlbumMiddleware 注入
) -> None:
    """仅处理 Photo 类型的图片上传 (支持单图和相册)"""
    
    # 1. 统一转换为列表处理
    media_list = album if album else [message]
    is_single = len(media_list) == 1
    
    # 2. 预检：过滤掉非 Photo 的消息（比如用户混着发了视频或文档）
    photo_messages = [m for m in media_list if m.photo]
    if not photo_messages:
        await message.answer("❌ 请发送图片（Photo），暂不支持文档或视频。")
        return

    # 3. 提取公共信息
    # 提取 Caption (相册中通常只有一张图带文字)
    common_caption = next((m.caption for m in photo_messages if m.caption), "")
    # 获取状态数据
    state_data = await state.get_data()
    is_nsfw = state_data.get("is_nsfw", False)
    
    success_count = 0
    last_model = None

    # 4. 循环保存图片
    for msg in photo_messages:
        await main_msg.delete_input(msg) # 删除用户发的消息
        
        # 获取最高画质的 PhotoSize 对象
        p = msg.photo[-1]
        file_id = p.file_id
        
        # 查重逻辑
        exists = await session.execute(select(MainImageModel.id).where(MainImageModel.file_id == file_id))
        if exists.scalar_one_or_none():
            if is_single:
                await send_toast(message, "❌ 图片重复了，请重新上传")
                return
            continue

        # 构建模型
        last_model = MainImageModel(
            file_id=file_id,
            source_type="photo",
            width=p.width,
            height=p.height,
            file_size=p.file_size,
            caption=common_caption,
            is_nsfw=is_nsfw,
        )
        session.add(last_model)
        success_count += 1

    # 5. 提交结果并反馈
    if success_count > 0:
        await session.commit()
        await session.refresh(last_model)

        safe_caption = escape_markdown_v2(common_caption)
        
        if is_single:
            # 单图模式：展示详细规格
            text = (
                "🎉 *图片上传成功！* 🌸\n\n"
                f"🆔 *ID*：`{last_model.id}`\n"
                f"🖼 *规格*：{last_model.width} × {last_model.height} ｜ "
                f"{escape_markdown_v2(format_size(last_model.file_size))}\n"
                f"{'🔞 NSFW' if is_nsfw else '🌿 SFW'}"
            )
            if common_caption:
                text += f"\n📝 {safe_caption}"
        else:
            # 多图模式：展示统计信息
            text = (
                f"🎉 *成功导入 {success_count} 张图片！* 🌸\n\n"
                f"🔞 *属性*：{'🔞 NSFW' if is_nsfw else '🌿 SFW'}\n"
                f"📝 *说明*：{safe_caption or '无'}"
            )

        await state.clear()
        await main_msg.render(message.from_user.id, text, get_main_image_upload_success_keyboard(is_nsfw))
    else:
        await message.answer("❌ 未能成功保存图片（可能已存在于库中）。")
