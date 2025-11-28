from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.menu import render_view
from bot.handlers.start import get_common_image
from bot.keyboards.inline.start_admin import get_admin_panel_keyboard
from bot.services.config_service import get_config, list_admin_permissions
from bot.utils.permissions import _resolve_role, require_admin_feature, require_admin_priv

router = Router(name="admin_panel")


@router.callback_query(F.data == "admin:panel")
@require_admin_priv
async def show_admin_panel(callback: CallbackQuery, session: AsyncSession) -> None:
    """展示管理员面板

    功能说明:
    - 展示二级管理员面板菜单, 底部包含返回主面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    perms = await list_admin_permissions(session)
    kb = get_admin_panel_keyboard(perms)
    user_id = callback.from_user.id if callback.from_user else None
    await _resolve_role(session, user_id)
    image = get_common_image()
    caption = "🛡️ 管理员面板"
    if callback.message:
        await render_view(callback.message, image, caption, kb)
    await callback.answer()


@router.callback_query(F.data == "admin:groups")
@require_admin_priv
@require_admin_feature("admin.groups")
async def open_groups_feature(callback: CallbackQuery, _session: AsyncSession) -> None:
    """打开群组管理功能

    功能说明:
    - 管理员面板中的群组管理入口占位处理, 功能关闭时提示不可用

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await callback.answer("功能建设中, 请使用 /admin_groups 命令", show_alert=True)


@router.callback_query(F.data == "admin:stats")
@require_admin_priv
@require_admin_feature("admin.stats")
async def open_stats_feature(callback: CallbackQuery, _session: AsyncSession) -> None:
    """打开统计数据功能

    功能说明:
    - 管理员面板中的统计数据入口占位处理, 功能关闭时提示不可用

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await callback.answer("功能建设中, 请使用 /admin_stats 命令", show_alert=True)


@router.callback_query(F.data == "admin:open_registration")
@require_admin_priv
@require_admin_feature("admin.open_registration")
async def open_registration_feature(callback: CallbackQuery, _session: AsyncSession) -> None:
    """打开开放注册功能

    功能说明:
    - 管理员面板中的开放注册入口占位处理, 功能关闭时提示不可用

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    await callback.answer("功能建设中", show_alert=True)


@router.callback_query(F.data == "admin:hitokoto")
@require_admin_priv
@require_admin_feature("admin.hitokoto")
async def open_hitokoto_feature(callback: CallbackQuery, session: AsyncSession) -> None:
    """打开一言管理功能

    功能说明:
    - 在管理员面板中展示一言分类选择面板

    输入参数:
    - callback: 回调对象
    - session: 异步数据库会话

    返回值:
    - None
    """
    categories: list[str] = await get_config(session, "admin.hitokoto.categories") or ["d", "i"]
    buttons: list[list[InlineKeyboardButton]] = []
    all_types = ["a","b","c","d","e","f","g","h","i","j","k","l"]
    for ch in all_types:
        enabled = ch in categories
        label = f"{ch.upper()} {'✅' if enabled else '❌'}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"admin:hitokoto:toggle:{ch}")])
    buttons.append([InlineKeyboardButton(text="保存并关闭", callback_data="admin:hitokoto:close")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    desc = (
        "📝 一言管理\n\n"
        "选择需要纳入的分类参数(多选):\n"
        "a 动画 | b 漫画 | c 游戏 | d 文学 | e 原创\n"
        "f 来自网络 | g 其他 | h 影视 | i 诗词 | j 网易云\n"
        "k 哲学 | l 抖机灵\n\n"
        f"当前分类: {', '.join(categories)}\n"
        "提示: 可多次点击切换, 保存后生效。"
    )
    if callback.message:
        await render_view(callback.message, get_common_image(), desc, kb)
    await callback.answer()
