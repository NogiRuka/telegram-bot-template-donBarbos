from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_SYMBOL
from bot.database.models import MediaCategoryModel, UserSubmissionModel
from bot.keyboards.inline.buttons import BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import USER_SUBMISSION_CALLBACK_DATA
from bot.services.currency import CurrencyService
from bot.services.main_message import MainMessageService
from bot.states.user import UserSubmitState
from bot.utils.message import send_toast
from bot.utils.text import escape_markdown_v2

router = Router(name="user_submit")

@router.callback_query(F.data == f"{USER_SUBMISSION_CALLBACK_DATA}:submit")
async def start_submit(callback: CallbackQuery, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """开始投稿"""
    
    # 获取可用的媒体分类
    stmt = select(MediaCategoryModel).where(
        MediaCategoryModel.is_enabled == True,
        MediaCategoryModel.is_deleted == False
    ).order_by(MediaCategoryModel.sort_order.asc(), MediaCategoryModel.id.asc())
    categories = (await session.execute(stmt)).scalars().all()
    
    if not categories:
        await callback.answer("⚠️ 暂无可用的分类", show_alert=True)
        return
    
    # 构建分类列表文本
    lines = []
    for i in range(0, len(categories), 5):
        row = categories[i:i + 5]
        line = "   ".join(
            f"{c.id}\\. {escape_markdown_v2(c.name)}"
            for c in row
        )
        lines.append(line)
    
    cat_text = "\n".join(lines)
    
    text = (
        "*✍️ 开始投稿*\n\n"
        "请发送您发现的优质内容，格式如下：\n\n"
        "`第1行：内容标题（必填）\n"
        "第2行：分类ID（见下方列表）\n"
        "第3行：详细描述（可选）\n"
        "第4行：其他备注（可选）`\n\n"
        "*📂 可用分类：*\n"
        f"{cat_text}\n\n"
        "💡 *提示：* 优质内容通过审核后可获得奖励\n"
        "📷 *支持图片：* 您可以发送图片，文字放在图片说明中"
    )
    
    # 创建键盘
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ 取消", callback_data=USER_SUBMISSION_CALLBACK_DATA)
    
    await main_msg.update_on_callback(callback, text, builder.as_markup())
    await state.set_state(UserSubmitState.waiting_for_input)
    await callback.answer()

from bot.utils.submission import parse_submit_input, SubmissionParseError

@router.message(UserSubmitState.waiting_for_input)
async def process_submit(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理用户投稿"""
    
    # 删除用户输入
    await main_msg.delete_input(message)
    
    # 获取文本内容
    text = message.text or message.caption
    if not text:
        await send_toast(message, "⚠️ 请输入文本内容")
        return
    
    try:
        # 解析用户输入
        parsed = await parse_submit_input(session, text)
        
        # 创建投稿记录
        user_id = message.from_user.id
        submission = UserSubmissionModel(
            title=parsed["title"],
            description=parsed.get("description", ""),
            type="submit",
            category_id=parsed["category_id"],
            status="pending",
            reward_base=3,  # 投稿基础奖励
            reward_bonus=5,  # 投稿额外奖励（审核通过后发放）
            submitter_id=user_id,
            extra={
                "submitted_by": user_id,
                "submission_type": "submit",
                "source": "user_direct",
                "has_image": bool(message.photo),
                "message_type": "photo" if message.photo else "text"
            }
        )
        
        session.add(submission)
        await session.flush()  # 获取ID
        
        # 如果有图片，保存图片信息
        if message.photo:
            photo = message.photo[-1]  # 获取最高质量图片
            file = await message.bot.get_file(photo.file_id)
            
            # 更新extra字段保存图片信息
            submission.extra.update({
                "photo_file_id": photo.file_id,
                "photo_file_unique_id": photo.file_unique_id,
                "photo_width": photo.width,
                "photo_height": photo.height,
                "file_path": file.file_path
            })
        
        # 发放基础奖励
        await CurrencyService.add_currency(
            session=session,
            user_id=user_id,
            amount=3,
            event_type="submit_submit",
            description=f"投稿提交 #{submission.id} 奖励"
        )
        
        await session.commit()
        
        # 发送群组通知
        try:
            from bot.utils.msg_group import send_group_notification
            
            user_info = {
                "user_id": str(user_id),
                "username": message.from_user.username or "Unknown",
                "full_name": message.from_user.full_name,
                "group_name": "UserSubmit",
                "action": "Submit",
            }
            
            reason = (
                f"提交了优质内容投稿（#{submission.id}）\n"
                f"📽️ {escape_markdown_v2(submission.title)}\n"
                f"🏷️ {escape_markdown_v2(parsed['category_name'])}"
            )
            
            # 如果有图片，发送图片通知
            if message.photo:
                photo = message.photo[-1]
                try:
                    from bot.utils.msg_group import send_group_photo_notification
                    await send_group_photo_notification(
                        message.bot, 
                        photo.file_id,
                        user_info, 
                        reason
                    )
                except Exception as e:
                    logger.warning(f"发送图片通知失败: {e}")
                    await send_group_notification(message.bot, user_info, reason)
            else:
                await send_group_notification(message.bot, user_info, reason)
        except Exception as e:
            logger.warning(f"发送群组通知失败: {e}")
        
        success_text = (
            f"✅ *投稿成功\\!*\n\n"
            f"📽️ 标题：{escape_markdown_v2(submission.title)}\n"
            f"🏷️ 分类：{escape_markdown_v2(parsed['category_name'])}\n"
            f"🎁 奖励：\\+3 {escape_markdown_v2(CURRENCY_SYMBOL)} 已发放\n\n"
            f"⏳ 请耐心等待管理员审核...\n"
            f"💡 审核通过后还将获得额外奖励"
        )
        
        # 退出状态
        await state.clear()
        
        # 返回成功界面
        builder = InlineKeyboardBuilder()
        builder.button(text="✍️ 继续投稿", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:submit")
        builder.button(text="📋 查看我的投稿", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:my_submissions")
        
        await main_msg.render(user_id, success_text, builder.as_markup())
        
    except SubmissionParseError as e:
        await send_toast(message, f"⚠️ {e}")
    except Exception as e:
        logger.error(f"用户投稿失败: {e}", exc_info=True)
        await send_toast(message, f"❌ 投稿失败: {e}")