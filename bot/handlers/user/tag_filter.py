"""
用户标签屏蔽功能处理器

功能说明:
- 管理用户屏蔽的标签列表
- 支持添加、移除、清空屏蔽标签
- 在消息处理时自动过滤屏蔽标签的内容
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from bot.database.models.user import UserModel
from bot.services.config_service import get_config
from bot.services.main_message import MainMessageService
from bot.config import KEY_USER_TAG_FILTER
from bot.utils.permissions import require_user_feature
from bot.keyboards.inline.common_buttons import BACK_BUTTON


# 创建路由器
router = Router(name="user_tag_filter")


@router.callback_query(F.data == "user:tag_filter")
@require_user_feature("user.tag_filter")
async def handle_user_tag_filter(
    callback_query: CallbackQuery,
    session: AsyncSession,
    main_message_service: MainMessageService,
    user: UserModel,
) -> None:
    """
    处理用户标签屏蔽功能主界面
    
    功能说明:
    - 显示当前屏蔽的标签列表
    - 提供管理屏蔽标签的选项
    
    输入参数:
    - callback_query: 回调查询对象
    - session: 数据库会话
    - main_message_service: 主消息服务
    - user: 当前用户模型
    
    返回值:
    - 无
    """
    
    # 检查功能是否启用
    config_value = await get_config(session, KEY_USER_TAG_FILTER)
    if not bool(config_value) if config_value is not None else False:
        await callback_query.answer("标签屏蔽功能已关闭", show_alert=True)
        return
    
    # 获取用户屏蔽的标签
    blocked_tags = user.tag_filter or []
    
    # 构建显示文本
    if blocked_tags:
        tags_text = "\n".join([f"• #{tag}" for tag in blocked_tags])
        text = f"🎯 当前屏蔽的标签 ({len(blocked_tags)}个):\n\n{tags_text}"
    else:
        text = "🎯 当前没有屏蔽任何标签\n\n你可以添加要屏蔽的标签关键词。"
    
    # 构建键盘
    keyboard = []
    
    # 管理选项
    keyboard.append([
        InlineKeyboardButton(text="➕ 添加屏蔽标签", callback_data="user:tag_filter:add"),
        InlineKeyboardButton(text="🗑️ 清空所有", callback_data="user:tag_filter:clear")
    ])
    
    # 如果已有屏蔽标签，显示移除选项
    if blocked_tags:
        keyboard.append([
            InlineKeyboardButton(text="❌ 移除标签", callback_data="user:tag_filter:remove")
        ])
    
    # 返回按钮
    keyboard.append([get_back_button()])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # 更新消息
    await main_message_service.update_message(
        text=text,
        reply_markup=markup,
    )
    
    await callback_query.answer()


@router.callback_query(F.data == "user:tag_filter:add")
@require_user_feature("user.tag_filter")
async def handle_add_tag_filter(
    callback_query: CallbackQuery,
    session: AsyncSession,
    main_message_service: MainMessageService,
) -> None:
    """
    处理添加屏蔽标签
    
    功能说明:
    - 提示用户输入要屏蔽的标签
    - 等待用户回复标签关键词
    
    输入参数:
    - callback_query: 回调查询对象
    - session: 数据库会话
    - main_message_service: 主消息服务
    
    返回值:
    - 无
    """
    
    text = """
🎯 添加屏蔽标签

请输入要屏蔽的标签关键词，多个标签用空格或逗号分隔。

例如:
• 广告 推广 营销
• 游戏, 电竞, 手游
• 股票 基金 理财

注意：输入的关键词不区分大小写。
    """.strip()
    
    # 设置用户状态，等待输入
    # TODO: 实现状态管理，等待用户回复
    
    await main_message_service.update_message(
        text=text,
        reply_markup=BACK_BUTTON,
    )
    
    await callback_query.answer("请在聊天中输入要屏蔽的标签关键词")


@router.callback_query(F.data == "user:tag_filter:remove")
@require_user_feature("user.tag_filter")
async def handle_remove_tag_filter(
    callback_query: CallbackQuery,
    session: AsyncSession,
    main_message_service: MainMessageService,
    user: UserModel,
) -> None:
    """
    处理移除屏蔽标签
    
    功能说明:
    - 显示当前屏蔽的标签列表
    - 用户可以选择要移除的标签
    
    输入参数:
    - callback_query: 回调查询对象
    - session: 数据库会话
    - main_message_service: 主消息服务
    - user: 当前用户模型
    
    返回值:
    - 无
    """
    
    blocked_tags = user.tag_filter or []
    
    if not blocked_tags:
        await callback_query.answer("没有可移除的标签", show_alert=True)
        return
    
    # 构建移除选项键盘
    keyboard = []
    for tag in blocked_tags:
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ #{tag}", 
                callback_data=f"user:tag_filter:remove:{tag}"
            )
        ])
    
    keyboard.append([get_back_button()])
    
    text = "🎯 选择要移除的屏蔽标签："
    
    await main_message_service.update_message(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    
    await callback_query.answer()


@router.callback_query(F.data.startswith("user:tag_filter:remove:"))
@require_user_feature("user.tag_filter")
async def handle_remove_specific_tag(
    callback_query: CallbackQuery,
    session: AsyncSession,
    main_message_service: MainMessageService,
    user: UserModel,
) -> None:
    """
    处理移除特定的屏蔽标签
    
    功能说明:
    - 从用户屏蔽列表中移除指定标签
    - 返回主界面
    
    输入参数:
    - callback_query: 回调查询对象
    - session: 数据库会话
    - main_message_service: 主消息服务
    - user: 当前用户模型
    
    返回值:
    - 无
    """
    
    # 提取要移除的标签
    tag_to_remove = callback_query.data.split(":", 3)[-1]
    
    # 获取当前屏蔽标签
    blocked_tags = user.tag_filter or []
    
    if tag_to_remove in blocked_tags:
        blocked_tags.remove(tag_to_remove)
        user.tag_filter = blocked_tags
        await session.commit()
        
        await callback_query.answer(f"已移除屏蔽标签: #{tag_to_remove}")
    else:
        await callback_query.answer("标签不存在")
    
    # 返回主界面
    await handle_user_tag_filter(
        callback_query, session, main_message_service, user
    )


@router.callback_query(F.data == "user:tag_filter:clear")
@require_user_feature("user.tag_filter")
async def handle_clear_tag_filter(
    callback_query: CallbackQuery,
    session: AsyncSession,
    main_message_service: MainMessageService,
    user: UserModel,
) -> None:
    """
    处理清空所有屏蔽标签
    
    功能说明:
    - 清空用户的所有屏蔽标签
    - 返回主界面
    
    输入参数:
    - callback_query: 回调查询对象
    - session: 数据库会话
    - main_message_service: 主消息服务
    - user: 当前用户模型
    
    返回值:
    - 无
    """
    
    # 清空屏蔽标签
    user.tag_filter = []
    await session.commit()
    
    await callback_query.answer("已清空所有屏蔽标签")
    
    # 返回主界面
    await handle_user_tag_filter(
        callback_query, session, main_message_service, user
    )


# 导出路由器
__all__ = ["router"]