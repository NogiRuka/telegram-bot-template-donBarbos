
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
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
async def handle_image_upload(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    main_msg: MainMessageService,
    album: list[Message] | None = None
) -> None:
    media_list = album if album else [message]
    is_single = len(media_list) == 1

    photo_messages = [m for m in media_list if m.photo]
    if not photo_messages:
        await message.answer("❌ 请发送图片（Photo）")
        return

    common_caption = next((m.caption for m in photo_messages if m.caption), "")
    state_data = await state.get_data()
    is_nsfw = state_data.get("is_nsfw", False)

    success_count = 0
    duplicate_count = 0
    last_model = None

    # 定义一个简单的“关闭提示”按钮
    close_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ 关闭提示", callback_data="delete_msg")]
    ])

    for msg in photo_messages:
        p = msg.photo[-1]
        file_id = p.file_id

        # 1. 查重逻辑
        exists = await session.execute(select(MainImageModel.id).where(MainImageModel.file_id == file_id))
        if exists.scalar_one_or_none():
            duplicate_count += 1
            # 【修改点】：不删除用户消息，发送带按钮的回复
            await msg.reply("⚠️ 该图片已存在于库中，已跳过。", reply_markup=close_kb)
            continue

        # 2. 只有不重复时，才删除用户发送的消息
        await main_msg.delete_input(msg)

        # 3. 保存逻辑
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

    # 4. 提交结果并反馈
    if success_count > 0:
        await session.commit()
        await session.refresh(last_model)

        safe_caption = escape_markdown_v2(common_caption)
        if is_single:
            text = (
                "🎉 *图片上传成功！*\n\n"
                f"🆔 *ID*：`{last_model.id}`\n"
                f"🖼 *规格*：{last_model.width} × {last_model.height} ｜ "
                f"{escape_markdown_v2(format_size(last_model.file_size))}\n"
                f"{'🔞 NSFW' if is_nsfw else '🌿 SFW'}"
            )
        else:
            text = f"🎉 *成功导入 {success_count} 张图片！*\n"
            if duplicate_count > 0:
                text += f"⚠️ 另有 {duplicate_count} 张重复已跳过原位保留。\n"
            text += f"\n🔞 *属性*：{'🔞 NSFW' if is_nsfw else '🌿 SFW'}"

        if common_caption:
            text += f"\n📝 {safe_caption}"

        # 渲染主控制面板
        await main_msg.render(message.from_user.id, text, get_main_image_upload_success_keyboard(is_nsfw))
        # 如果你希望传完一批就结束状态，保留 clear；如果想连续传，建议删掉 state.clear()
        await state.clear()

    elif duplicate_count > 0:
        # 如果全是重复的，更新主面板提示一下
        await main_msg.render(
            message.from_user.id,
            "⚠️ 您发送的图片均已存在，已为您在原位标注。",
            get_main_image_upload_success_keyboard(is_nsfw)
        )
