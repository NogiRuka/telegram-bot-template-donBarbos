"""
管理员服务模块

提供管理员操作的核心业务逻辑，如封禁用户、清理数据等。
"""

from aiogram import Bot
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import (
    ActionType,
    AuditLogModel,
    EmbyUserModel,
    UserExtendModel,
)
from bot.services.emby_update_helper import detect_and_update_emby_user
from bot.utils.datetime import now
from bot.utils.emby import get_emby_client
from bot.utils.msg_group import send_group_notification


async def ban_emby_user(
    session: AsyncSession,
    target_user_id: int,
    admin_id: int | None = None,
    reason: str = "封禁",
    bot: Bot | None = None,
    user_info: dict[str, str] | None = None,
) -> list[str]:
    """
    封禁 Emby 用户逻辑

    功能:
    1. 删除 Emby 账号 (API)
    2. 软删除数据库 Emby 用户数据
    3. 记录审计日志
    4. 发送通知到管理员群组 (如果配置)

    Args:
        session: 数据库会话
        target_user_id: 目标 Telegram 用户 ID
        admin_id: 执行操作的管理员 ID (可选)
        reason: 封禁原因
        bot: Bot 实例 (用于发送通知)
        user_info: 用户信息字典 (username, full_name, group_name 等)

    Returns:
        操作结果消息列表
    """
    results = []

    # 查找 Emby 关联
    stmt = select(UserExtendModel).where(UserExtendModel.user_id == target_user_id)
    result = await session.execute(stmt)
    user_extend = result.scalar_one_or_none()

    emby_user_id = None
    if user_extend and user_extend.emby_user_id:
        emby_user_id = user_extend.emby_user_id

    deleted_by = admin_id if admin_id else 0  # 0 表示系统或未知

    # 获取 Emby 账号名称
    emby_name = "Unknown"
    emby_user_db = None
    if emby_user_id:
        stmt_emby = select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id)
        result_emby = await session.execute(stmt_emby)
        emby_user_db = result_emby.scalar_one_or_none()
        if emby_user_db:
            emby_name = emby_user_db.name

    api_status = "skipped"
    api_error_msg = ""

    # 1. 删除 Emby 账号 (API)
    # 如果数据库中标记为已软删除，则跳过 API 调用 (认为已经被删了)
    if emby_user_id:
        is_already_deleted = emby_user_db and emby_user_db.is_deleted

        if is_already_deleted:
            api_status = "already_deleted_skip"
        else:
            emby_client = get_emby_client()
            if emby_client:
                try:
                    await emby_client.delete_user(emby_user_id)
                    api_status = "success"
                except Exception as e:
                    error_str = str(e)
                    if "404" in error_str:
                        api_status = "404"
                    else:
                        api_status = "error"
                        api_error_msg = error_str
                        logger.error(f"❌ 删除 Emby 账号失败: {e}")
            else:
                api_status = "not_configured"

    # 2. 软删除数据库 EmbyUserModel
    db_status = "skipped"
    deleted_devices_count = 0
    if emby_user_db:
        # 如果已经被删除了，就不重复记录了，但还是要记录审计日志
        if not emby_user_db.is_deleted:
            emby_user_db.is_deleted = True
            emby_user_db.deleted_at = now()
            emby_user_db.deleted_by = deleted_by
            emby_user_db.remark = f"{reason} (操作者: {deleted_by})"
            db_status = "success"

            # 同时软删除该用户关联的设备
            from bot.database.models.emby_device import EmbyDeviceModel
            stmt_devices = (
                select(EmbyDeviceModel)
                .where(
                    EmbyDeviceModel.last_user_id == emby_user_db.emby_user_id,
                    EmbyDeviceModel.is_deleted.is_(False),
                )
            )
            res_devices = await session.execute(stmt_devices)
            devices = res_devices.scalars().all()
            for device in devices:
                device.is_deleted = True
                device.deleted_at = now()
                device.deleted_by = deleted_by
                device.remark = f"用户被封禁自动删除 (操作者: {deleted_by})"

            if devices:
                deleted_devices_count = len(devices)
        else:
            db_status = "already_deleted"

    # 生成结果消息 (MarkdownV2 格式)
    from bot.utils.text import escape_markdown_v2

    def fmt_name(n: str) -> str:
        return f"`{escape_markdown_v2(n)}`"

    if not emby_user_id:
        results.append("ℹ️ 该用户未绑定 Emby 账号")
    elif api_status == "not_configured":
        results.append(f"❌ Emby API 未配置 ，跳过账号删除（{fmt_name(emby_name)}）")
    elif api_status == "error":
        safe_err = escape_markdown_v2(api_error_msg)
        results.append(f"❌ Emby 账号删除失败: {safe_err}")
    elif api_status == "404":
        results.append(f"ℹ️ Emby 账号已软删除 （{fmt_name(emby_name)}）")
    elif api_status == "already_deleted_skip":
        results.append(f"ℹ️ Emby 账号此前已软删除，跳过 API 调用 （{fmt_name(emby_name)}）")
    elif api_status == "success":
        results.append(f"✅ Emby 账号已删除（{fmt_name(emby_name)}）")
    elif db_status in {"success", "already_deleted"}:
        results.append(f"ℹ️ Emby 账号已软删除 （{fmt_name(emby_name)}）")
    else:
        results.append(f"ℹ️ Emby 账号状态未知 ({fmt_name(emby_name)})")

    if deleted_devices_count > 0:
        results.append(f"ℹ️ 自动软删除 {deleted_devices_count} 个关联设备")

    # 3. 记录审计日志
    audit_log = AuditLogModel(
        operator_id=deleted_by,
        user_id=target_user_id,
        action_type=ActionType.USER_BLOCK,  # 使用 USER_BLOCK 作为封禁/移除的操作类型
        target_id=str(target_user_id),
        description=f"封禁用户 {target_user_id}",  # 必填字段
        details={
            "emby_user_id": emby_user_id,
            "reason": reason,
            "results": results,
            "source": "auto_ban_on_leave" if not admin_id else "manual_ban"
        },
        ip_address="127.0.0.1", # 内部操作
        user_agent="System/Bot"
    )
    session.add(audit_log)

    # 4. 发送通知到管理员群组
    if bot and user_info:
        # 确保 user_id 存在
        user_info["user_id"] = str(target_user_id)

        # 将处理结果加入原因中，以便在通知中显示
        # results 已经是 MarkdownV2 格式，直接使用
        results_str = "\n".join([f"{r}" for r in results])

        # 对 reason 本身也进行转义（假设它是纯文本）
        from bot.utils.text import escape_markdown_v2
        escaped_reason = escape_markdown_v2(reason)

        detailed_reason = f"{escaped_reason}\n{results_str}"

        # 调用通用通知函数
        await send_group_notification(bot, user_info, detailed_reason)

    return results


async def disable_emby_user(
    session: AsyncSession,
    target_id: str,  # 可以是 Telegram ID 或 Emby ID
    admin_id: int | None = None,
    reason: str = "管理员手动禁用",
    bot: Bot | None = None,
    user_info: dict[str, str] | None = None,
) -> list[str]:
    """
    禁用 Emby 用户逻辑

    功能:
    1. 禁用 Emby 账号 (API)
    2. 更新数据库状态
    3. 记录审计日志
    4. 发送通知

    Args:
        session: 数据库会话
        target_id: 目标 ID (Telegram ID 或 Emby ID)
        admin_id: 执行操作的管理员 ID (可选)
        reason: 禁用原因
        bot: Bot 实例 (用于发送通知)
        user_info: 用户信息字典
    """
    results = []
    
    # 1. 确定目标 Emby 用户
    emby_user_id = None
    emby_user_db = None

    # 尝试按 Telegram ID 查找
    if target_id.isdigit():
        stmt = select(UserExtendModel).where(UserExtendModel.user_id == int(target_id))
        result = await session.execute(stmt)
        user_extend = result.scalar_one_or_none()
        if user_extend and user_extend.emby_user_id:
            emby_user_id = user_extend.emby_user_id

    # 如果没找到，尝试按 Emby ID 查找
    if not emby_user_id:
        # 假设 target_id 就是 Emby ID
        emby_user_id = target_id

    # 查找 Emby 用户记录
    stmt_emby = select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id)
    result_emby = await session.execute(stmt_emby)
    emby_user_db = result_emby.scalar_one_or_none()

    if not emby_user_db:
        return ["❌ 未找到对应的 Emby 用户记录"]

    # 2. 调用 API 禁用
    emby_client = get_emby_client()
    if not emby_client:
        return ["⚠️ Emby 客户端未配置"]

    try:
        success = await emby_client.disable_user(emby_user_id)
        if success:
            results.append("✅ Emby 账号已禁用")
            
            # 重新获取 UserDto 以保持同步
            new_user_dto = await emby_client.get_user(emby_user_id)
            
            # 更新数据库状态
            from sqlalchemy.orm.attributes import flag_modified
            from bot.utils.datetime import format_datetime

            # 使用通用更新逻辑
            detect_and_update_emby_user(
                model=emby_user_db,
                new_user_dto=new_user_dto or emby_user_db.user_dto or {},
                session=session,
                force_update=True,
                extra_remark=f"{reason} (禁用)"
            )

            # 额外更新 extra_data
            if not emby_user_db.extra_data:
                emby_user_db.extra_data = {}
            
            emby_user_db.extra_data["is_disabled"] = True
            emby_user_db.extra_data["disabled_reason"] = "manual_ban"
            emby_user_db.extra_data["disabled_at"] = format_datetime(now())
            emby_user_db.extra_data["disabled_by"] = admin_id
            
            flag_modified(emby_user_db, "extra_data")
            session.add(emby_user_db)
            await session.commit()
            
            # 发送通知给用户
            if bot:
                # 尝试获取 Telegram ID
                tg_user_id = None
                
                # 1. 检查是否已经是 Telegram ID
                if target_id.isdigit():
                    # 验证是否关联到当前 Emby 用户
                    stmt_check = select(UserExtendModel).where(
                        UserExtendModel.user_id == int(target_id),
                        UserExtendModel.emby_user_id == emby_user_id
                    )
                    res_check = await session.execute(stmt_check)
                    if res_check.scalar_one_or_none():
                        tg_user_id = int(target_id)
                
                # 2. 如果还没有 Telegram ID，尝试通过 Emby ID 反查
                if not tg_user_id:
                    stmt_find = select(UserExtendModel).where(UserExtendModel.emby_user_id == emby_user_id)
                    res_find = await session.execute(stmt_find)
                    user_ext = res_find.scalar_one_or_none()
                    if user_ext and user_ext.user_id:
                        tg_user_id = user_ext.user_id
                
                if tg_user_id:
                    try:
                        await bot.send_message(
                            chat_id=tg_user_id,
                            text=(
                                "桜色男孩⚣｜账号状态通知 🚫\n\n"
                                "您的 Emby 账号已被管理员禁用。\n\n"
                                f"📝 原因: {reason}\n"
                                f"⏰ 时间: {format_datetime(now())}\n\n"
                                "如有疑问，请联系管理员。"
                            )
                        )
                        results.append(f"📨 已发送通知给用户 {tg_user_id}")
                    except Exception as e:
                        logger.warning(f"无法发送禁用通知给用户 {tg_user_id}: {e}")
                        results.append(f"⚠️ 无法发送通知: {e}")
            
        else:
            results.append("⚠️ Emby API 禁用请求失败或用户已禁用")

    except Exception as e:
        logger.error(f"禁用 Emby 用户失败: {e}")
        results.append(f"❌ API 错误: {e}")

    # 3. 记录审计日志
    audit_log = AuditLogModel(
        operator_id=admin_id if admin_id else 0,
        action_type=ActionType.USER_BLOCK,
        target_type="emby_user",
        target_id=str(emby_user_id),
        description=f"禁用 Emby 用户 {emby_user_id}",
        details={"action": "disable", "reason": reason, "target_id": target_id},
        ip_address="127.0.0.1",
        user_agent="System/Bot"
    )
    session.add(audit_log)
    await session.commit()

    return results


async def enable_emby_user(
    session: AsyncSession,
    target_id: str,
    admin_id: int | None = None,
    reason: str = "管理员手动启用",
    bot: Bot | None = None,
    user_info: dict[str, str] | None = None,
) -> list[str]:
    """
    启用 Emby 用户逻辑

    功能:
    1. 启用 Emby 账号 (API)
    2. 更新数据库状态
    3. 记录审计日志
    4. 发送通知
    """
    results = []
    
    # 1. 确定目标 Emby 用户
    emby_user_id = None
    emby_user_db = None

    if target_id.isdigit():
        stmt = select(UserExtendModel).where(UserExtendModel.user_id == int(target_id))
        result = await session.execute(stmt)
        user_extend = result.scalar_one_or_none()
        if user_extend and user_extend.emby_user_id:
            emby_user_id = user_extend.emby_user_id

    if not emby_user_id:
        emby_user_id = target_id

    stmt_emby = select(EmbyUserModel).where(EmbyUserModel.emby_user_id == emby_user_id)
    result_emby = await session.execute(stmt_emby)
    emby_user_db = result_emby.scalar_one_or_none()

    if not emby_user_db:
        return ["❌ 未找到对应的 Emby 用户记录"]

    # 2. 调用 API 启用
    emby_client = get_emby_client()
    if not emby_client:
        return ["⚠️ Emby 客户端未配置"]

    try:
        success = await emby_client.enable_user(emby_user_id)
        if success:
            results.append("✅ Emby 账号已启用")
            
            new_user_dto = await emby_client.get_user(emby_user_id)
            
            from sqlalchemy.orm.attributes import flag_modified
            
            detect_and_update_emby_user(
                model=emby_user_db,
                new_user_dto=new_user_dto or emby_user_db.user_dto or {},
                session=session,
                force_update=True,
                extra_remark=f"{reason} (启用)"
            )

            if not emby_user_db.extra_data:
                emby_user_db.extra_data = {}
            
            # 清除禁用状态
            emby_user_db.extra_data["is_disabled"] = False
            emby_user_db.extra_data.pop("disabled_reason", None)
            emby_user_db.extra_data.pop("disabled_at", None)
            emby_user_db.extra_data.pop("disabled_by", None)
            
            flag_modified(emby_user_db, "extra_data")
            session.add(emby_user_db)
            await session.commit()
            
            # 发送通知给用户
            if bot:
                # 尝试获取 Telegram ID
                tg_user_id = None
                
                # 1. 检查是否已经是 Telegram ID
                if target_id.isdigit():
                    # 验证是否关联到当前 Emby 用户
                    stmt_check = select(UserExtendModel).where(
                        UserExtendModel.user_id == int(target_id),
                        UserExtendModel.emby_user_id == emby_user_id
                    )
                    res_check = await session.execute(stmt_check)
                    if res_check.scalar_one_or_none():
                        tg_user_id = int(target_id)
                
                # 2. 如果还没有 Telegram ID，尝试通过 Emby ID 反查
                if not tg_user_id:
                    stmt_find = select(UserExtendModel).where(UserExtendModel.emby_user_id == emby_user_id)
                    res_find = await session.execute(stmt_find)
                    user_ext = res_find.scalar_one_or_none()
                    if user_ext and user_ext.user_id:
                        tg_user_id = user_ext.user_id
                
                if tg_user_id:
                    try:
                        await bot.send_message(
                            chat_id=tg_user_id,
                            text=(
                                "桜色男孩⚣｜账号状态通知 ✅\n\n"
                                "您的 Emby 账号已被管理员重新启用。\n\n"
                                f"📝 原因: {reason}\n"
                                f"⏰ 时间: {format_datetime(now())}\n\n"
                                "现在您可以正常使用 Emby 服务了～"
                            )
                        )
                        results.append(f"📨 已发送通知给用户 {tg_user_id}")
                    except Exception as e:
                        logger.warning(f"无法发送启用通知给用户 {tg_user_id}: {e}")
                        results.append(f"⚠️ 无法发送通知: {e}")
            
        else:
            results.append("⚠️ Emby API 启用请求失败或用户已启用")

    except Exception as e:
        logger.error(f"启用 Emby 用户失败: {e}")
        results.append(f"❌ API 错误: {e}")

    # 3. 记录审计日志
    audit_log = AuditLogModel(
        operator_id=admin_id if admin_id else 0,
        action_type=ActionType.USER_UNBLOCK,
        target_type="emby_user",
        target_id=str(emby_user_id),
        description=f"启用 Emby 用户 {emby_user_id}",
        details={"action": "enable", "reason": reason, "target_id": target_id},
        ip_address="127.0.0.1",
        user_agent="System/Bot"
    )
    session.add(audit_log)
    await session.commit()

    return results


async def unban_user_service(
    session: AsyncSession,
    target_user_id: int,
    admin_id: int | None = None,
    reason: str = "解封",
    bot: Bot | None = None,
    user_info: dict[str, str] | None = None,
) -> list[str]:
    """
    解封用户服务逻辑

    功能:
    1. 记录审计日志
    2. 发送通知到管理员群组

    Args:
        session: 数据库会话
        target_user_id: 目标 Telegram 用户 ID
        admin_id: 执行操作的管理员 ID
        reason: 解封原因
        bot: Bot 实例
        user_info: 用户信息字典

    Returns:
        操作结果消息列表
    """
    results = []
    operator_id = admin_id if admin_id else 0

    # 记录审计日志
    audit_log = AuditLogModel(
        user_id=operator_id,
        action_type=ActionType.USER_UNBLOCK,
        target_id=str(target_user_id),
        description=f"解封用户 {target_user_id}",  # 必填字段
        details={
            "reason": reason,
            "source": "manual_unban"
        },
        ip_address="127.0.0.1",
        user_agent="System/Bot"
    )
    session.add(audit_log)
    results.append("✅ 已记录解封审计日志")

    # 发送通知到管理员群组
    if bot and user_info:
        user_info["user_id"] = str(target_user_id)

        # 将处理结果加入原因中
        from bot.utils.text import escape_markdown_v2
        results_str = "\n".join([f"{escape_markdown_v2(r)}" for r in results])
        escaped_reason = escape_markdown_v2(reason)
        detailed_reason = f"{escaped_reason}\n{results_str}"

        await send_group_notification(bot, user_info, detailed_reason)

    return results
