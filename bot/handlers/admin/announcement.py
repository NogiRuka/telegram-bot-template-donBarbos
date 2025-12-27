from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_ANNOUNCEMENT, KEY_ANNOUNCEMENT_TEXT
from bot.keyboards.inline.buttons import BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import ANNOUNCEMENT_LABEL
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService
from bot.utils.message import delete_message_after_delay
from bot.utils.permissions import require_admin_feature, require_admin_priv

router = Router(name="admin_announcement")


class AnnouncementStates(StatesGroup):
    """公告编辑状态组

    功能说明:
    - 管理员编辑公告文案时进入此状态

    输入参数:
    - 无

    返回值:
    - None
    """

    waiting_for_text = State()


def _build_panel_ui(current_text: str | None) -> tuple[str, InlineKeyboardBuilder]:
    """构建公告面板的 UI 内容

    功能说明:
    - 根据当前公告内容生成 caption 和 keyboard

    输入参数:
    - current_text: 当前公告文本

    返回值:
    - tuple[str, InlineKeyboardBuilder]: (caption, keyboard_builder)
    """
    display_text = current_text if current_text else "（当前未设置公告）"
    caption = (
        f"{ANNOUNCEMENT_LABEL}\n\n"
        f"当前公告：\n{display_text}\n\n"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✏️ 编辑公告", callback_data="admin:announcement:edit"),
        InlineKeyboardButton(text="🗑️ 清空公告", callback_data="admin:announcement:clear"),
    )
    kb.row(BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON)
    
    return caption, kb


@router.callback_query(F.data == "admin:announcement")
@require_admin_priv
@require_admin_feature(KEY_ADMIN_ANNOUNCEMENT)
async def open_announcement_panel(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """打开公告管理面板

    功能说明:
    - 展示当前公告文案(如有)
    - 提供编辑与清空公告的入口

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    current_text = await get_config(session, KEY_ANNOUNCEMENT_TEXT)
    current_text = (str(current_text).strip() if current_text is not None else "")
    
    caption, kb = _build_panel_ui(current_text)

    await main_msg.update_on_callback(callback, caption, kb.as_markup())


@router.callback_query(F.data == "admin:announcement:edit")
@require_admin_priv
@require_admin_feature(KEY_ADMIN_ANNOUNCEMENT)
async def start_edit_announcement(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始编辑公告

    功能说明:
    - 进入等待公告文本输入状态
    - 更新主消息提示管理员输入公告内容

    输入参数:
    - callback: 回调对象
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    await state.set_state(AnnouncementStates.waiting_for_text)
    caption = (
        "✏️ 请输入新的公告文案：\n\n"
        "限制：建议不超过 1000 字（Telegram 单条消息最大约 4096 字）\n"
        "提示：发送文本后将立即生效"
    )
    kb = InlineKeyboardBuilder()
    kb.row(BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON)
    await main_msg.update_on_callback(callback, caption, kb.as_markup())


@router.callback_query(F.data == "admin:announcement:clear")
@require_admin_priv
@require_admin_feature(KEY_ADMIN_ANNOUNCEMENT)
async def clear_announcement(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """清空公告文案

    功能说明:
    - 将公告配置值置空，不在首页展示

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - main_msg: 主消息服务

    返回值:
    - None
    """
    await set_config(session, KEY_ANNOUNCEMENT_TEXT, None)

    # 直接更新界面，避免重新查库
    caption, kb = _build_panel_ui(None)

    await main_msg.update_on_callback(callback, caption, kb.as_markup())
    await callback.answer("公告已清空")


@router.message(AnnouncementStates.waiting_for_text)
async def handle_announcement_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    main_msg: MainMessageService,
) -> None:
    """处理公告文本输入

    功能说明:
    - 将管理员发送的文本保存到配置表
    - 删除用户输入并更新主消息面板

    输入参数:
    - message: 管理员消息
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务

    返回值:
    - None
    """
    text = (message.text or "").strip()
    await state.clear()
    await main_msg.delete_input(message)

    if not text:
        # 如果文本为空，不做更新，或者提示错误（这里因为删除了输入，可能需要发送临时消息或忽略）
        # 简单起见，如果为空，直接返回到面板
        pass
    else:
        ok = await set_config(session, KEY_ANNOUNCEMENT_TEXT, text)
        if not ok:
            # 更新失败，发送临时提示
            temp_msg = await message.answer("🔴 更新失败，请稍后重试")
            delete_message_after_delay(temp_msg, 5)
            return
        
        # 更新成功，发送临时提示
        success_msg = await message.answer("✅ 公告已更新")
        delete_message_after_delay(success_msg, 3)

    # 无论成功与否（只要非空或空），都尝试刷新主面板显示最新状态
    # 重新查询以确保显示的是数据库中的最新值
    current_text = await get_config(session, KEY_ANNOUNCEMENT_TEXT)
    current_text = (str(current_text).strip() if current_text is not None else "")
    
    caption, kb = _build_panel_ui(current_text)

    if message.from_user:
        await main_msg.update(message.from_user.id, caption, kb.as_markup())
