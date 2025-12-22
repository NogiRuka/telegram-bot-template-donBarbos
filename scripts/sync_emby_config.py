import asyncio
import sys
from pathlib import Path

# Add project root to path
# Use parent of parent because this script is in scripts/ folder
sys.path.append(str(Path(__file__).parent.parent))

import contextlib
from datetime import datetime

from loguru import logger
from sqlalchemy import select, desc

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
                all_users = [{"Id": u.emby_user_id, "Name": u.name, "MaxDevices": u.max_devices} for u in db_users]
                
                # 检查是否有未找到的用户
                found_ids = set(u["Id"] for u in all_users)
                for uid in specific_user_ids:
                    if uid not in found_ids:
                         # 尝试从 API 获取作为补充? 或者直接标记未知
                         # 这里简单处理，如果DB没有，就跳过或加个Unknown
                         all_users.append({"Id": uid, "Name": "Unknown", "MaxDevices": 3})
            else:
                # 未指定用户，拉取所有用户
                stmt = select(EmbyUserModel)
                res = await session.execute(stmt)
                db_users = res.scalars().all()
                all_users = [{"Id": u.emby_user_id, "Name": u.name, "MaxDevices": u.max_devices} for u in db_users]
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

            if uid in skips and not specific_user_ids:
                 pass
            elif uid in skips:
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
                
                if len(devices) <= max_devices:
                    enabled_ids = [d.reported_device_id for d in devices if d.reported_device_id]
                else:
                    # 1. 根据 AppName 去重保留最新
                    app_map = {}
                    for d in devices:
                        app_name = d.app_name or "Unknown"
                        if app_name not in app_map:
                            app_map[app_name] = d
                        else:
                            current = app_map[app_name]
                            # 比较最后活动时间
                            d_time = d.date_last_activity or datetime.min
                            c_time = current.date_last_activity or datetime.min
                            if d_time > c_time:
                                app_map[app_name] = d
                    
                    unique_devices = list(app_map.values())
                    
                    # 2. 根据最后活动时间保留最新的 max_devices 个
                    unique_devices.sort(key=lambda x: x.date_last_activity or datetime.min, reverse=True)
                    keep_devices = unique_devices[:max_devices]
                    
                    enabled_ids = [d.reported_device_id for d in keep_devices if d.reported_device_id]
                    
                    # 3. 标记废弃设备
                    keep_ids = set(d.id for d in keep_devices)
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
                user_policy["EnableAllDevices"] = False  # 必须关闭此项以使 EnabledDevices 生效

                # 更新 Configuration
                await client.update_user_configuration(uid, template_config)
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
        "945e1aa74d964da183b3e6a0f0075d6f"
    ]

    # 针对失败用户进行重试
    specific_ids = [
        
    ]

    _success, _fail = await sync_all_users_configuration(exclude_user_ids=exclude_ids, specific_user_ids=specific_ids)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
