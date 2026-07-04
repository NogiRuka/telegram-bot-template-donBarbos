from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.constants import CURRENCY_SYMBOL
from bot.database.models import UserSubmissionModel
from bot.database.models.library_new_notification import LibraryNewNotificationModel
from bot.handlers.command._usage import build_usage_text
from bot.keyboards.inline.buttons import CLOSE_BUTTON
from bot.services.currency import CurrencyService
from bot.utils.datetime import now
from bot.utils.message import send_toast
from bot.utils.permissions import require_admin_command_access, require_admin_priv

router = Router(name="command_submission_review")

COMMAND_META = {
    "name": "sr",
    "alias": "submission_review",
    "usage": {
        "summary": [
            "/sr <投稿ID> <操作> [留言]",
            "通过支持: a / approve，可选附带通知ID",
            "拒绝支持: r / reject，直接填写留言即可",
        ],
        "formats": [
            "/sr <投稿ID> a [通知ID] [留言]",
            "/sr <投稿ID> r [留言]",
        ],
        "examples": [
            "/sr 12 a 35 已收录，感谢投稿",
            "/sr 12 r 资源信息不完整",
        ],
    },
    "desc": "命令式投稿审批"
}


@router.message(Command(commands=["sr", "submission_review"]))
@require_admin_priv
@require_admin_command_access(COMMAND_META["name"])
async def cmd_submission_review(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """命令式投稿审批（/sr, /submission_review）

    功能说明:
    - 通过命令快速审批用户求片/投稿，并可附带留言
    - 命令格式:
      - 通过: /sr <submission_id> <a/approve> [notif_id] [comment...]
      - 拒绝: /sr <submission_id> <r/reject> [comment...]
      - submission_id: 求片/投稿ID（整数）
      - a/r: a=通过(approve)，r=拒绝(reject)
      - notif_id: 关联的通知ID（LibraryNewNotificationModel.id，仅通过时可选）
      - comment: 审批留言（可选，支持空格；当未提供notif_id时，如第三参数非纯数字则视为comment）
    - 审批通过时若 reward_bonus>0，将发放奖励
    - 将投稿者ID追加到对应通知的 target_user_id（逗号分隔，去重）

    输入参数:
    - message: 文本消息对象
    - command: 命令对象（包含原始参数）
    - session: 异步数据库会话

    返回值:
    - None

    Telegram API 说明与限制:
    - 单条消息长度建议不超过 4096 字符
    - 发送速率受限于 Telegram（约每秒 30 次），出现429需重试
    - 仅在 Bot 能主动私聊用户且未被屏蔽时可成功通知投稿者
    """
    try:
        args_raw = (command.args or "").strip()
        parts = args_raw.split()
        if len(parts) < 2:
            await send_toast(message, f"❌ 参数不足\n{build_usage_text(COMMAND_META)}", parse_mode="Markdown")
            return

        submission_id_str, action_str = parts[0], parts[1]
        notif_id: int | None = None
        comment = ""

        action = action_str.lower()
        if action not in ("a", "approve", "r", "reject"):
            await send_toast(message, "❌ 操作类型无效，应为 a/approve 或 r/reject")
            return

        if len(parts) >= 3:
            if action in ("a", "approve"):
                third = parts[2]
                if third.isdigit():
                    notif_id = int(third)
                    comment = " ".join(parts[3:]) if len(parts) > 3 else ""
                else:
                    comment = " ".join(parts[2:])
            else:
                comment = " ".join(parts[2:])

        try:
            submission_id = int(submission_id_str)
        except ValueError:
            await send_toast(message, "❌ 投稿ID或通知ID必须为整数")
            return

        submission = await session.get(UserSubmissionModel, submission_id)
        if not submission:
            await send_toast(message, f"❌ 投稿不存在：#{submission_id}")
            return
        if submission.status != "pending":
            await send_toast(message, f"⚠️ 投稿状态已改变，当前为：{submission.status}")
            return

        notification: LibraryNewNotificationModel | None = None
        if notif_id is not None:
            notification = await session.get(LibraryNewNotificationModel, notif_id)
            if not notification:
                await send_toast(message, f"❌ 通知不存在：#{notif_id}")
                return

        submission.reviewer_id = message.from_user.id if message.from_user else None
        submission.review_time = now()
        if comment:
            submission.review_comment = comment

        if action in ("a", "approve"):
            submission.status = "approved"
            if submission.reward_bonus and submission.reward_bonus > 0:
                try:
                    await CurrencyService.add_currency(
                        session=session,
                        user_id=submission.submitter_id,
                        amount=submission.reward_bonus,
                        event_type="submission_approve",
                        description=f"投稿 #{submission.id} 审核通过奖励"
                    )
                except Exception as e:
                    logger.warning(f"❌ 发放奖励失败: {e}")
            result_text = "✅ 审核通过"
        else:
            submission.status = "rejected"
            result_text = "❌ 审核拒绝"

        try:
            if notification is not None:
                existing = notification.target_user_id or ""
                existing_ids = {int(x.strip()) for x in existing.split(",") if x.strip().isdigit()}
                existing_ids.add(int(submission.submitter_id))
                notification.target_user_id = ",".join(str(x) for x in sorted(existing_ids))
                notification.updated_by = message.from_user.id if message.from_user else None
        except Exception as e:
            logger.warning(f"❌ 更新通知 target_user_id 失败: {e}")

        await session.commit()

        try:
            type_text = "投稿" if submission.type == "submit" else "求片"
            base_text = f"{result_text}，您的{type_text} *{submission.title}* 已处理。\n"
            if comment:
                base_text += f"📝 管理员留言：{comment}\n"
            if submission.status == "approved" and submission.reward_bonus and submission.reward_bonus > 0:
                base_text += f"🎁 奖励：+{submission.reward_bonus} {CURRENCY_SYMBOL}\n"
            await message.bot.send_message(
                submission.submitter_id,
                base_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"❌ 通知投稿者 {submission.submitter_id} 失败: {e}")
        kb = InlineKeyboardMarkup(inline_keyboard=[[CLOSE_BUTTON]])
        if submission.status == "approved" and notification is not None:
            await message.reply(
                f"{result_text}。\n"
                f"📄 投稿ID：{submission.id}\n"
                f"🔗 通知ID：{notification.id}\n"
                f"👤 已记录需额外通知的用户ID：`{notification.target_user_id or '无'}`",
                reply_markup=kb,
            parse_mode="MarkdownV2"
            )
        elif submission.status == "approved":
            await message.reply(
                f"{result_text}。\n"
                f"📄 投稿ID：{submission.id}\n"
                f"🔗 通知ID：未提供（未追加通知用户）",
                reply_markup=kb,
            parse_mode="MarkdownV2"
            )
        else:
            reply_text = f"{result_text}。\n📄 投稿ID：{submission.id}"
            if comment:
                reply_text += f"\n📝 留言：{comment}"
            await message.reply(
                reply_text,
                reply_markup=kb,
                parse_mode="MarkdownV2"
            )

    except Exception as e:
        logger.exception(f"❌ /sr 命令处理失败: {e}")
        await message.answer(f"❌ 处理失败：{e}")
