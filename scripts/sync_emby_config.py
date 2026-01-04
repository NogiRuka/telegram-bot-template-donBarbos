import asyncio
import sys
from pathlib import Path

# Add project root to path
# Use parent of parent because this script is in scripts/ folder
sys.path.append(str(Path(__file__).parent.parent))

import contextlib
from datetime import datetime

from loguru import logger
from sqlalchemy import select

from bot.core.config import settings
from bot.database.database import sessionmaker
from bot.database.models.emby_device import EmbyDeviceModel
from bot.database.models.emby_user import EmbyUserModel
from bot.utils.datetime import now
from bot.utils.emby import get_emby_client


async def sync_all_users_configuration(
    exclude_user_ids: list[str] | None = None,
    specific_user_ids: list[str] | None = None,
) -> tuple[int, int]:
    """批量同步所有用户的 Configuration 和 Policy 为模板用户配置

    功能说明:
    - 遍历所有 Emby 用户
    - 将 Configuration 和 Policy 更新为模板用户的一致配置
    - 支持 exclude_user_ids 排除特定用户
    - 支持 specific_user_ids 仅同步特定用户 (优先级高于 exclude)

    输入参数:
    - exclude_user_ids: 要跳过的用户ID列表
    - specific_user_ids: 仅同步的用户ID列表

    返回值:
    - tuple[int, int]: (成功更新数量, 失败数量)
    """
    client = get_emby_client()
    if client is None:
        logger.warning("⚠️ 未配置 Emby 连接信息, 无法同步配置")
        return 0, 0

    tid = settings.get_emby_template_user_id()
    if not tid:
        logger.warning("⚠️ 未配置 Emby 模板用户ID (EMBY_TEMPLATE_USER_ID), 无法同步配置")
        return 0, 0

    # 获取模板用户详情
    try:
        template_user = await client.get_user(tid)
    except Exception as e:
        logger.error(f"❌ 获取模板用户({tid})失败: {e}")
        return 0, 0

    template_config = template_user.get("Configuration")
    template_policy = template_user.get("Policy")

    if not isinstance(template_config, dict) or not isinstance(template_policy, dict):
        logger.error("❌ 模板用户的 Configuration 或 Policy 格式错误")
        return 0, 0

    # 准备排除列表
    skips = set(exclude_user_ids or [])
    skips.add(tid)  # 排除模板用户自己

    success_count = 0
    fail_count = 0

    async with sessionmaker() as session:
        # 获取目标用户列表 (从数据库获取)
        all_users = []
        try:
            if specific_user_ids:
                # 指定了用户ID列表
                stmt = select(EmbyUserModel).where(EmbyUserModel.emby_user_id.in_(specific_user_ids))
                res = await session.execute(stmt)
                db_users = res.scalars().all()
                all_users = [{"Id": u.emby_user_id, "Name": u.name, "MaxDevices": u.max_devices, "UserDto": u.user_dto} for u in db_users]

                # 检查是否有未找到的用户
                found_ids = {u["Id"] for u in all_users}
                for uid in specific_user_ids:
                    if uid not in found_ids:
                         # 尝试从 API 获取作为补充? 或者直接标记未知
                         # 这里简单处理，如果DB没有，就跳过或加个Unknown
                         all_users.append({"Id": uid, "Name": "Unknown", "MaxDevices": 3, "UserDto": {}})
            else:
                # 未指定用户，拉取所有用户
                # 排除 exclude_user_ids 中的用户
                stmt = select(EmbyUserModel)
                if exclude_user_ids:
                    stmt = stmt.where(EmbyUserModel.emby_user_id.notin_(exclude_user_ids))

                res = await session.execute(stmt)
                db_users = res.scalars().all()
                all_users = [{"Id": u.emby_user_id, "Name": u.name, "MaxDevices": u.max_devices, "UserDto": u.user_dto} for u in db_users]
        except Exception as e:
            logger.error(f"❌ 从数据库获取用户列表失败: {e}")
            return 0, 0

        logger.info(f"🔄 开始批量同步 Emby 用户配置, 模板用户: {tid}, 目标用户数: {len(all_users)}")

        for user in all_users:
            uid = user.get("Id")
            name = user.get("Name")
            # 优先使用数据库中的配置，如果没有则默认3
            max_devices = user.get("MaxDevices", 3)

            if not uid:
                continue

            if uid in skips:
                 logger.debug(f"⏭️ 跳过用户: {name} ({uid})")
                 continue

            try:
                # 查询用户设备
                stmt = select(EmbyDeviceModel).where(
                    EmbyDeviceModel.last_user_id == uid,
                    EmbyDeviceModel.is_deleted == False
                )
                res = await session.execute(stmt)
                devices = res.scalars().all()

                enabled_ids = []
                enable_all_devices = False

                if len(devices) < max_devices:
                    # Case 1: 设备数 < 最大限制
                    # 允许新设备登录 (EnableAllDevices=True)
                    # 同时更新 EnabledDevices 为当前列表 (虽不强制生效，但在切换状态时有用)
                    enabled_ids = [d.reported_device_id for d in devices if d.reported_device_id]
                    enable_all_devices = True
                elif len(devices) == max_devices:
                    # Case 2: 设备数 = 最大限制
                    # 禁止新设备 (EnableAllDevices=False)
                    # 仅允许现有设备
                    enabled_ids = [d.reported_device_id for d in devices if d.reported_device_id]
                    enable_all_devices = False
                else:
                    # Case 3: 设备数 > 最大限制 (执行清理)
                    enable_all_devices = False

                    # 直接按最后活动时间排序，保留最新的 max_devices 个
                    # 之前使用 AppName 去重逻辑会导致多开浏览器场景下误删
                    # sorted_devices = sorted(devices, key=lambda x: x.date_last_activity or datetime.min, reverse=True)
                    # 由于 devices 是从 DB 取出的，可能已经是某种顺序，但显式排序更安全
                    devices.sort(key=lambda x: x.date_last_activity or datetime.min, reverse=True)
                    keep_devices = devices[:max_devices]

                    enabled_ids = [d.reported_device_id for d in keep_devices if d.reported_device_id]

                    # 3. 标记废弃设备
                    keep_ids = {d.id for d in keep_devices}
                    has_changes = False
                    for d in devices:
                        if d.id not in keep_ids:
                            d.is_deleted = True
                            d.deleted_at = now()
                            d.deleted_by = 0  # 0 表示系统
                            d.remark = "超出最大设备数自动清理"
                            session.add(d)
                            has_changes = True

                    if has_changes:
                        await session.commit()
                        logger.info(f"🧹 用户 {name} 设备清理: 总数 {len(devices)} -> 保留 {len(keep_devices)}")

                # 构建新的 Policy
                user_policy = template_policy.copy()
                user_policy["EnabledDevices"] = enabled_ids
                user_policy["EnableAllDevices"] = enable_all_devices

                # 检查是否需要更新
                # 获取当前 Policy (从 DB 中的 UserDto 获取，避免额外 API 调用)
                current_user_dto = user.get("UserDto") or {}
                current_policy = current_user_dto.get("Policy", {})

                # 比较 EnabledDevices (注意 Emby 返回的可能是 list，我们需要 set 比较且忽略顺序)
                current_enabled = set(current_policy.get("EnabledDevices", []))
                new_enabled = set(enabled_ids)

                current_all = current_policy.get("EnableAllDevices", False)
                # 注意: Emby 有时返回 None 或缺省值，需确保类型一致

                if current_enabled == new_enabled and current_all == enable_all_devices:
                    logger.debug(f"⏭️ 配置未变更，跳过更新: {name} ({uid})")
                    continue

                # 更新 Policy
                await client.update_user_policy(uid, user_policy)
                logger.debug(f"✅ 已更新用户配置: {name} ({uid})")
                success_count += 1
            except Exception as e:
                logger.error(f"❌ 更新用户配置失败: {name} ({uid}) -> {e}")
                fail_count += 1

    logger.info(f"✅ 批量同步完成: 成功 {success_count}, 失败 {fail_count}")
    return success_count, fail_count


async def main() -> None:
    logger.info("开始执行 Emby 用户配置批量同步...")

    # 用户指定的排除 ID
    exclude_ids = [
        "52588e7dbcbe4ea7a575dfe86a7f4a28",
        "945e1aa74d964da183b3e6a0f0075d6f",
        "0e26758dc85d40488314f9d77d8c9a7d"
    ]

    # 针对失败用户进行重试
    specific_ids = [
        # "ed43223312414d80accfdb722ddddc47"
    ]

    _success, _fail = await sync_all_users_configuration(exclude_user_ids=exclude_ids, specific_user_ids=specific_ids)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
