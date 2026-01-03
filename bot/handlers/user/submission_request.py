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
from bot.states.user import UserRequestState
from bot.utils.message import send_toast
from bot.utils.text import escape_markdown_v2

router = Router(name="user_request")

@router.callback_query(F.data == f"{USER_SUBMISSION_CALLBACK_DATA}:request")
async def start_request(callback: CallbackQuery, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """开始求片"""
    
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
        "*📥 开始求片*\n\n"
        "请发送您想要的影片信息，格式如下：\n\n"
        "`第1行：影片标题（必填）\n"
        "第2行：分类ID（见下方列表）\n"
        "第3行：详细描述（可选）\n"
        "第4行：其他备注（可选）`\n\n"
        "*📂 可用分类：*\n"
        f"{cat_text}\n\n"
        "💡 *提示：* 您也可以直接发送标题，系统会自动分类\n"
        "📷 *支持图片：* 您可以发送图片，文字放在图片说明中"
    )
    
    # 创建键盘
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ 取消", callback_data=USER_SUBMISSION_CALLBACK_DATA)
    
    await main_msg.update_on_callback(callback, text, builder.as_markup())
    await state.set_state(UserRequestState.waiting_for_input)
    await callback.answer()

from bot.utils.submission import parse_request_input, SubmissionParseError

@router.message(UserRequestState.waiting_for_input)
async def process_request(message: Message, state: FSMContext, session: AsyncSession, main_msg: MainMessageService) -> None:
    """处理用户求片"""
    
    # 删除用户输入
    await main_msg.delete_input(message)
    
    # 获取文本内容
    text = message.text or message.caption
    if not text:
        await send_toast(message, "⚠️ 请输入文本内容")
        return
    
    try:
        # 解析用户输入
        parsed = await parse_request_input(session, text)
        
        # 创建求片记录
        user_id = message.from_user.id
        submission = UserSubmissionModel(
            title=parsed["title"],
            description=parsed.get("description", ""),
            type="request",
            category_id=parsed["category_id"],
            status="pending",
            reward_base=0,  # 求片不发放奖励
            reward_bonus=0,
            submitter_id=user_id,
            extra={
                "submitted_by": user_id,
                "submission_type": "request",
                "source": "user_direct"
            }
        )
        
        # 如果有图片，保存图片信息到专用字段
        if message.photo:
            photo = message.photo[-1]  # 获取最高质量图片
            submission.image_file_id = photo.file_id
            submission.image_file_unique_id = photo.file_unique_id
        
        session.add(submission)
        await session.flush()  # 获取ID
        await session.commit()
        
        # 发送群组通知
        try:
            from bot.utils.msg_group import send_group_notification
            
            user_info = {
                "user_id": str(user_id),
                "username": message.from_user.username or "Unknown",
                "full_name": message.from_user.full_name,
                "group_name": "UserRequest",
                "action": "Submit",
            }
            
            reason = (
                f"提交了求片请求（#{submission.id}）\n"
                f"📽️ {escape_markdown_v2(submission.title)}\n"
                f"🏷️ {escape_markdown_v2(parsed['category_name'])}"
            )
            
            await send_group_notification(message.bot, user_info, reason)
        except Exception as e:
            logger.warning(f"发送群组通知失败: {e}")
        
        success_text = (
            f"✅ *求片成功\\!*\n\n"
            f"📽️ 标题：{escape_markdown_v2(submission.title)}\n"
            f"🏷️ 分类：{escape_markdown_v2(parsed['category_name'])}\n\n"
            f"⏳ 请耐心等待管理员审核..."
        )
        
        # 退出状态
        await state.clear()
        
        # 返回成功界面
        builder = InlineKeyboardBuilder()
        builder.button(text="📥 继续求片", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:request")
        builder.button(text="📋 查看我的求片", callback_data=f"{USER_SUBMISSION_CALLBACK_DATA}:my_submissions")
        builder.row(BACK_TO_PROFILE_BUTTON, BACK_TO_HOME_BUTTON)
        
        await main_msg.render(user_id, success_text, builder.as_markup())
        
    except SubmissionParseError as e:
        await send_toast(message, f"⚠️ {e}")
    except Exception as e:
        logger.error(f"用户求片失败: {e}", exc_info=True)
        await send_toast(message, f"❌ 求片失败: {e}")