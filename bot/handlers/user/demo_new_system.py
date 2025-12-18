"""
新功能开发流程演示

功能说明:
展示如何使用统一的功能注册系统开发新功能
实现"只改一个地方"的开发目标
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.features import register_user_feature, get_user_feature_button
from bot.services.config_service import get_config_bool
from bot.services.main_message import MainMessageService
from bot.config import KEY_USER_DEMO
from bot.utils.permissions import require_user_feature
from bot.keyboards.inline.common_buttons import get_back_button


# 创建路由器
router = Router(name="demo")


# 定义处理器
@router.callback_query(F.data == "user:demo")
@require_user_feature("user.demo")
async def handle_user_demo(
    callback_query: CallbackQuery,
    session: AsyncSession,
    main_message_service: MainMessageService,
) -> None:
    """
    处理用户演示功能
    
    功能说明:
    - 演示如何使用新的功能注册系统
    - 展示简化后的开发流程
    
    输入参数:
    - callback_query: 回调查询对象
    - session: 数据库会话
    - main_message_service: 主消息服务
    
    返回值:
    - 无
    """
    
    # 检查功能是否启用
    if not await get_config_bool(session, KEY_USER_DEMO):
        await callback_query.answer("演示功能已关闭", show_alert=True)
        return
    
    # 演示功能逻辑
    text = """
🎉 欢迎使用新的功能开发系统！

✨ 特点:
• 一键生成功能代码
• 自动注册按钮和处理器
• 支持功能开关控制
• 统一权限管理

🚀 开发流程大大简化！
    """.strip()
    
    # 更新消息
    await main_message_service.update_message(
        text=text,
        reply_markup=get_back_button(),
    )
    
    await callback_query.answer()


# 注册功能 - 这是唯一需要手动添加的地方！
register_user_feature(
    name="user.demo",
    label="演示功能",
    description="展示新的功能开发流程",
    handler=handle_user_demo,
    enabled=True,
    show_in_panel=True,
    button_order=50,
)


# 导出路由器
__all__ = ["router"]