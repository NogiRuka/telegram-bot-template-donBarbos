from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.constants import KEY_ADMIN_MAIN_IMAGE, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED
from bot.keyboards.inline.admin import get_main_image_admin_keyboard
from bot.keyboards.inline.constants import MAIN_IMAGE_ADMIN_CALLBACK_DATA
from bot.services.config_service import get_config, set_config
from bot.services.main_message import MainMessageService
from bot.utils.permissions import require_admin_feature
from .router import router

@router.callback_query(F.data == MAIN_IMAGE_ADMIN_CALLBACK_DATA)
@require_admin_feature(KEY_ADMIN_MAIN_IMAGE)
async def show_main_image_panel(callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """展示主图管理面板
    
    功能说明:
    - 显示主图管理的二级面板, 包含上传/列表/节日投放/测试/NSFW开关
    - 清除当前可能存在的状态
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    await state.clear()
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
async def toggle_nsfw(callback: CallbackQuery, session: AsyncSession, state: FSMContext, main_msg: MainMessageService) -> None:
    """切换 NSFW 全局开关
    
    功能说明:
    - 切换 admin.main_image.nsfw_enabled 配置项, 并刷新面板
    
    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话
    - state: FSM 上下文
    - main_msg: 主消息服务
    
    返回值:
    - None
    """
    current = bool(await get_config(session, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED) or False)
    await set_config(session, KEY_ADMIN_MAIN_IMAGE_NSFW_ENABLED, (not current), config_type=None, operator_id=callback.from_user.id)
    # 刷新面板 (复用 show_main_image_panel)
    await show_main_image_panel(callback, session, state, main_msg)
