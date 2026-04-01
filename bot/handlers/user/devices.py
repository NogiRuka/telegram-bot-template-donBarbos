from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.core.config import settings
from bot.database.models.emby_device import EmbyDeviceModel
from bot.database.models.emby_user import EmbyUserModel
from bot.database.models.user_extend import UserExtendModel
from bot.keyboards.inline.buttons import BACK_TO_ACCOUNT_BUTTON, BACK_TO_HOME_BUTTON
from bot.keyboards.inline.constants import USER_DEVICES_LABEL
from bot.services.main_message import MainMessageService
from bot.services.emby_service import build_device_diff, build_device_snapshot, create_device_history
from bot.utils.datetime import now
from bot.utils.emby import get_emby_client
from bot.utils.permissions import require_emby_account, require_user_feature

router = Router(name="user_devices")


async def _update_emby_policy(session: AsyncSession, emby_user_id: str, max_devices: int) -> bool:
    """更新 Emby 用户 Policy (根据设备数量)

    功能说明:
    - 获取用户当前未删除的设备
    - 如果数量 < max_devices: EnableAllDevices = True
    - 如果数量 >= max_devices: EnableAllDevices = False, EnabledDevices = [设备ID列表]
    """
    client = get_emby_client()
    if not client:
        return False

    # 0. 检查是否为模板用户
    if emby_user_id == settings.get_emby_template_user_id():
        logger.info(f"⏭️ 跳过排除用户(模板) Policy 更新: {emby_user_id}")
        return True

    try:
        # 1. 获取当前有效设备
        stmt = (
            select(EmbyDeviceModel)
            .where(
                EmbyDeviceModel.last_user_id == emby_user_id,
                EmbyDeviceModel.is_deleted.is_(False),
            )
        )
        res = await session.execute(stmt)
        devices = res.scalars().all()

        current_count = len(devices)
        enabled_ids = [d.reported_device_id for d in devices if d.reported_device_id]

        # 2. 获取用户现有 Policy
        user_dto = await client.get_user(emby_user_id)
        if not user_dto:
            return False

        policy = user_dto.get("Policy", {})

        # 检查是否为管理员
        if policy.get("IsAdministrator", False):
            logger.info(f"⏭️ 跳过排除用户(管理员) Policy 更新: {emby_user_id}")
            return True

        # 3. 根据规则修改 Policy
        if current_count < max_devices:
            # 小于最大数：允许所有设备
            policy["EnableAllDevices"] = True
            # 可选：清空 EnabledDevices 或保持原样，EnableAllDevices=True 时通常忽略此字段
            # 但为了保持整洁，可以更新为当前设备列表
            policy["EnabledDevices"] = enabled_ids
        else:
            # 大于等于最大数：仅允许列表中的设备
            policy["EnableAllDevices"] = False
            policy["EnabledDevices"] = enabled_ids

        # 4. 提交更新
        await client.update_user_policy(emby_user_id, policy)
        logger.info(f"✅ 更新 Emby Policy 成功: User={emby_user_id}, Count={current_count}/{max_devices}, AllowAll={policy['EnableAllDevices']}")
        return True

    except Exception as e:
        logger.error(f"❌ 更新 Emby Policy 失败: {e}")
        return False


@router.callback_query(F.data == "user:devices")
@require_user_feature("user.devices")
@require_emby_account
async def user_devices(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """设备管理

    功能说明:
    - 显示用户当前设备列表
    - 显示最大设备限制
    - 提供删除设备的按钮
    """
    user_id = callback.from_user.id

    # 1. 获取关联的 Emby 用户 ID
    stmt = select(UserExtendModel.emby_user_id).where(UserExtendModel.user_id == user_id)
    res = await session.execute(stmt)
    emby_user_id = res.scalar_one_or_none()

    # 同步最新设备状态
    # try:
    #     await save_all_emby_devices(session)
    #     await cleanup_devices_by_policy(session)
    # except Exception as e:
    #     logger.warning(f"⚠️ 进入设备管理页面时同步失败: {e}")

    # 2. 获取 Emby 用户信息 (最大设备数)
    stmt_user = select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id)
    res_user = await session.execute(stmt_user)
    emby_user = res_user.scalar_one_or_none()

    max_devices = emby_user.max_devices if emby_user else 3

    # 3. 获取设备列表
    stmt_devices = (
        select(EmbyDeviceModel)
        .where(
            EmbyDeviceModel.last_user_id == emby_user_id,
            EmbyDeviceModel.is_deleted.is_(False),
        )
        .order_by(EmbyDeviceModel.date_last_activity.desc())
    )

    res_devices = await session.execute(stmt_devices)
    devices = res_devices.scalars().all()

    # 4. 构建界面
    device_count = len(devices)
    status_icon = "🟢" if device_count <= max_devices else "🔴"

    text = (
        f"*{USER_DEVICES_LABEL}*\n\n"
        f"当前设备数：{device_count} / {max_devices} {status_icon}\n"
        f"规则：仅小于 {max_devices} 个设备时允许新设备。\n\n"
        "点击设备按钮可将其移除👇"
    )
    kb = InlineKeyboardBuilder()

    for device in devices:
        # 显示格式: 设备名 (应用名)
        btn_text = f"{device.name or 'Unknown'} ({device.app_name or 'App'})"
        # 截断过长的名称
        if len(btn_text) > 30:
            btn_text = btn_text[:28] + ".."

        kb.row(InlineKeyboardButton(
            text=f"{btn_text}",
            callback_data=f"user:device:delete:{device.id}"
        ))

    kb.row(BACK_TO_ACCOUNT_BUTTON, BACK_TO_HOME_BUTTON)

    await main_msg.update_on_callback(callback, text, kb.as_markup())


from bot.utils.text import escape_markdown_v2


@router.callback_query(F.data.startswith("user:device:delete:"))
@require_emby_account
async def handle_device_delete_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """处理删除设备确认"""
    try:
        device_pk = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ 无效的请求", show_alert=True)
        return

    user_id = callback.from_user.id

    # 1. 验证权限
    stmt = select(UserExtendModel.emby_user_id).where(UserExtendModel.user_id == user_id)
    res = await session.execute(stmt)
    emby_user_id = res.scalar_one_or_none()

    stmt_device = select(EmbyDeviceModel).where(
        EmbyDeviceModel.id == device_pk,
        EmbyDeviceModel.last_user_id == emby_user_id
    )
    res_device = await session.execute(stmt_device)
    device = res_device.scalar_one_or_none()

    if not device:
        await callback.answer("❌ 设备不存在或无权操作", show_alert=True)
        return

    # 2. 弹出确认框
    last_active = device.date_last_activity.strftime("%Y-%m-%d %H:%M") if device.date_last_activity else "未知"

    # 转义设备名称和 App 名称
    name_esc = escape_markdown_v2(device.name or "Unknown")
    app_esc = escape_markdown_v2(device.app_name or "App")
    last_active_esc = escape_markdown_v2(last_active)

    device_info = f"{name_esc} \\({app_esc}\\)\n最后活跃：{last_active_esc}"
    text = f"⚠️ *确认删除设备?*\n\n设备：{device_info}\n\n删除后该设备将无法连接服务器。"

    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ 确认删除", callback_data=f"user:device:confirm_del:{device_pk}"),
        InlineKeyboardButton(text="❌ 取消", callback_data="user:devices")
    )

    await main_msg.update_on_callback(callback, text, kb.as_markup())


@router.callback_query(F.data.startswith("user:device:confirm_del:"))
async def handle_device_delete_action(
    callback: CallbackQuery,
    session: AsyncSession,
    main_msg: MainMessageService
) -> None:
    """执行删除设备操作"""
    try:
        device_pk = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("❌ 无效的请求", show_alert=True)
        return

    user_id = callback.from_user.id

    # 1. 验证权限
    stmt = select(UserExtendModel).where(UserExtendModel.user_id == user_id)
    res = await session.execute(stmt)
    user_extend = res.scalar_one_or_none()

    if not user_extend or not user_extend.emby_user_id:
        await callback.answer("❌ 未绑定 Emby 账号", show_alert=True)
        return

    emby_user_id = user_extend.emby_user_id

    stmt_device = select(EmbyDeviceModel).where(
        EmbyDeviceModel.id == device_pk,
        EmbyDeviceModel.last_user_id == emby_user_id
    )
    res_device = await session.execute(stmt_device)
    device = res_device.scalar_one_or_none()

    if not device:
        await callback.answer("❌ 设备不存在或无权操作", show_alert=True)
        return

    if device.is_deleted:
        await callback.answer("⚠️ 设备已被删除", show_alert=True)
        await user_devices(callback, session, main_msg)
        return

    # 2. 软删除设备
    before_data = build_device_snapshot(device)
    device.is_deleted = True
    device.deleted_at = now()
    device.deleted_by = user_id
    device.remark = "用户手动删除"
    after_data = build_device_snapshot(device)
    changed_fields, diff_data = build_device_diff(before_data, after_data)
    session.add(
        create_device_history(
            device=device,
            action="delete",
            source="user",
            before_data=before_data,
            after_data=after_data,
            changed_fields=changed_fields,
            diff_data=diff_data,
            remark=device.remark,
            operator_id=user_id,
        )
    )

    # 3. 获取最大设备数
    stmt_user = select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id)
    res_user = await session.execute(stmt_user)
    emby_user = res_user.scalar_one_or_none()
    max_devices = emby_user.max_devices if emby_user else 3

    # 4. 更新 Policy (需要先 commit 确保 query 能查到最新的 is_deleted 状态?
    # 不，同一个 session 中 query 会看到 flush 后的变化，或者我们手动传参)
    # 这里我们先 flush 让 DB 状态更新，但 update_emby_policy 里用的是同一个 session 吗？
    # 是的，传入了 session。

    # 注意: _update_emby_policy 内部做了 select，如果没 commit，
    # 在某些隔离级别下可能查不到？
    # SQLAlchemy asyncio session 默认是 repeatable read 吗？
    # 最好先 commit 或者是 flush。
    # 这里 device.is_deleted = True 只是在内存/session 中。
    # _update_emby_policy 里的 select 会使用当前 session，所以能看到变更。

    await session.flush()

    # 调用 Policy 更新
    success = await _update_emby_policy(session, emby_user_id, max_devices)

    if success:
        await session.commit()
        await callback.answer("✅ 设备已删除", show_alert=False)
    else:
        await session.rollback()
        await callback.answer("🔴 删除失败", show_alert=True)

    # 5. 刷新界面
    await user_devices(callback, session, main_msg)

