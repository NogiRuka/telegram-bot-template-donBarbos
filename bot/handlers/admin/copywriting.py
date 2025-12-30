from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_ANNOUNCEMENT, KEY_ADMIN_ANNOUNCEMENT_TEXT, KEY_USER_LINES_NOTICE
from bot.keyboards.inline.buttons import BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_COPYWRITING_BUTTON, BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import ADMIN_COPYWRITING_CALLBACK_DATA, COPYWRITING_LABEL
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService
from bot.utils.message import delete_message_after_delay
from bot.utils.permissions import require_admin_feature, require_admin_priv

router = Router(name="admin_copywriting")


class CopywritingStates(StatesGroup):
    """文案编辑状态组"""
    waiting_for_text = State()


# 定义支持的文案类型配置
COPYWRITING_TYPES = {
    "announcement": {
        "label": "📢 公告消息",
        "key": KEY_ADMIN_ANNOUNCEMENT_TEXT,
        "description": "首页公告内容，支持 MarkdownV2。"
    },
    "notice": {
        "label": "📝 服务须知",
        "key": KEY_USER_LINES_NOTICE,
        "description": "线路信息面板底部的服务须知，支持 MarkdownV2。"
    }
}


@router.callback_query(F.data == ADMIN_COPYWRITING_CALLBACK_DATA)
@require_admin_priv
@require_admin_feature(KEY_ADMIN_ANNOUNCEMENT)
async def open_copywriting_menu(callback: CallbackQuery, main_msg: MainMessageService) -> None:
    """文案管理主菜单

    功能说明:
    - 展示所有可管理的文案类型列表
    """
    caption = f"*{COPYWRITING_LABEL}*\n\n请选择要管理的文案类型："

    kb = InlineKeyboardBuilder()
    for type_code, info in COPYWRITING_TYPES.items():
        kb.row(InlineKeyboardButton(
            text=info["label"],
            callback_data=f"admin:copywriting:view:{type_code}"
        ))

    kb.row(BACK_TO_ADMIN_PANEL_BUTTON, BACK_TO_HOME_BUTTON)
    await main_msg.update_on_callback(callback, caption, kb.as_markup())


@router.callback_query(F.data.startswith("admin:copywriting:view:"))
@require_admin_priv
@require_admin_feature(KEY_ADMIN_ANNOUNCEMENT)
async def view_copywriting(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """查看特定文案内容"""
    type_code = callback.data.split(":")[-1]
    if type_code not in COPYWRITING_TYPES:
        await callback.answer("❌ 未知类型")
        return

    info = COPYWRITING_TYPES[type_code]
    config_key = info["key"]

    content = await get_config(session, config_key)
    content = (str(content).strip() if content is not None else "")
    display_content = content if content else "（当前未设置）"

    caption = (
        f"*{info['label']}*\n\n"
        f"{info['description']}\n\n"
        f"当前内容：\n{display_content}\n\n"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✏️ 编辑内容", callback_data=f"admin:copywriting:edit:{type_code}"),
        InlineKeyboardButton(text="🗑️ 清空内容", callback_data=f"admin:copywriting:clear:{type_code}"),
    )
    kb.row(BACK_TO_COPYWRITING_BUTTON, BACK_TO_HOME_BUTTON)

    await main_msg.update_on_callback(callback, caption, kb.as_markup())


@router.callback_query(F.data.startswith("admin:copywriting:edit:"))
@require_admin_priv
@require_admin_feature(KEY_ADMIN_ANNOUNCEMENT)
async def start_edit_copywriting(callback: CallbackQuery, state: FSMContext, main_msg: MainMessageService) -> None:
    """开始编辑文案"""
    type_code = callback.data.split(":")[-1]
    if type_code not in COPYWRITING_TYPES:
        await callback.answer("❌ 未知类型")
        return

    info = COPYWRITING_TYPES[type_code]

    await state.set_state(CopywritingStates.waiting_for_text)
    await state.update_data(target_type=type_code)

    caption = (
        f"✏️ 正在编辑：*{info['label']}*\n\n"
        "请输入新的文案内容：\n"
        "提示：支持 MarkdownV2 格式，发送文本后立即生效。"
    )

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 取消编辑", callback_data=f"admin:copywriting:view:{type_code}"))

    await main_msg.update_on_callback(callback, caption, kb.as_markup())


@router.callback_query(F.data.startswith("admin:copywriting:clear:"))
@require_admin_priv
@require_admin_feature(KEY_ADMIN_ANNOUNCEMENT)
async def clear_copywriting(callback: CallbackQuery, session: AsyncSession, main_msg: MainMessageService) -> None:
    """清空文案"""
    type_code = callback.data.split(":")[-1]
    if type_code not in COPYWRITING_TYPES:
        await callback.answer("❌ 未知类型")
        return

    info = COPYWRITING_TYPES[type_code]
    config_key = info["key"]

    await set_config(session, config_key, None)
    await callback.answer("✅ 内容已清空")

    # 刷新界面
    await view_copywriting(callback, session, main_msg)


@router.message(CopywritingStates.waiting_for_text)
async def handle_copywriting_text(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    main_msg: MainMessageService
) -> None:
    """处理文案输入"""
    text = (message.text or "").strip()
    data = await state.get_data()
    type_code = data.get("target_type")

    await state.clear()
    await main_msg.delete_input(message)

    if not type_code or type_code not in COPYWRITING_TYPES:
        return

    info = COPYWRITING_TYPES[type_code]
    config_key = info["key"]

    if text:
        ok = await set_config(session, config_key, text)
        if ok:
            msg = await message.answer(f"✅ {info['label']} 已更新")
            delete_message_after_delay(msg, 3)
        else:
            msg = await message.answer("🔴 更新失败，请稍后重试")
            delete_message_after_delay(msg, 5)

    # 返回查看界面
    content = await get_config(session, config_key)
    content = (str(content).strip() if content is not None else "")
    display_content = content if content else "（当前未设置）"

    caption = (
        f"*{info['label']}*\n\n"
        f"{info['description']}\n\n"
        f"当前内容：\n{display_content}\n\n"
    )

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✏️ 编辑内容", callback_data=f"admin:copywriting:edit:{type_code}"),
        InlineKeyboardButton(text="🗑️ 清空内容", callback_data=f"admin:copywriting:clear:{type_code}"),
    )
    kb.row(BACK_TO_COPYWRITING_BUTTON, BACK_TO_HOME_BUTTON)

    if message.from_user:
        await main_msg.render(message.from_user.id, caption, kb.as_markup())
