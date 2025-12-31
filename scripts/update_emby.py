import asyncio
import sys
from pathlib import Path

# Add project root to path
# Use parent of parent because this script is in scripts/ folder
sys.path.append(str(Path(__file__).parent.parent))

import contextlib

from loguru import logger
from sqlalchemy import select

from bot.database.database import sessionmaker
from bot.database.models.emby_user import EmbyUserModel
from bot.utils.emby import get_emby_client


async def sync_all_users_configuration(  # noqa: C901
    exclude_user_ids: list[str] | None = None,
    specific_user_ids: list[str] | None = None,
) -> tuple[int, int]:
    """批量同步用户 Policy(强制设置为 False)

    功能说明:
    - 遍历所有 Emby 用户
    - 仅更新 Policy: 将 EnableUserPreferenceAccess 强制设为 False(不关心原值)
    - 不修改 Configuration(语言偏好等保持原样)
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

    # 准备排除列表
    skips = set(exclude_user_ids or [])

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
                all_users = [{"Id": u.emby_user_id, "Name": u.name, "UserDto": u.user_dto} for u in db_users]

                # 检查是否有未找到的用户
                found_ids = {u["Id"] for u in all_users}
                for uid in specific_user_ids:
                    if uid not in found_ids:
                         all_users.append({"Id": uid, "Name": "Unknown", "UserDto": {}})
            else:
                # 未指定用户, 拉取所有用户
                # 排除 exclude_user_ids 中的用户
                stmt = select(EmbyUserModel)
                if exclude_user_ids:
                    stmt = stmt.where(EmbyUserModel.emby_user_id.notin_(exclude_user_ids))

                res = await session.execute(stmt)
                db_users = res.scalars().all()
                all_users = [{"Id": u.emby_user_id, "Name": u.name, "UserDto": u.user_dto} for u in db_users]
        except Exception as e:  # noqa: BLE001
            logger.error(f"❌ 从数据库获取用户列表失败: {e}")
            return 0, 0

        logger.info(f"🔄 开始批量更新 Emby 用户配置 (语言偏好 & 权限), 目标用户数: {len(all_users)}")

        for user in all_users:
            uid = user.get("Id")
            name = user.get("Name")

            if not uid:
                continue

            if uid in skips:
                 logger.info(f"⏭️ 跳过用户: {name} ({uid})")
                 continue

            try:
                # 获取当前 UserDto (从 DB)
                current_user_dto = user.get("UserDto") or {}
                current_policy = current_user_dto.get("Policy", {})
                current_user_dto.get("Configuration", {})

                # --- 处理 Policy(强制设为 False) ---
                user_policy = current_policy.copy()
                user_policy["EnableUserPreferenceAccess"] = False

                await client.update_user_policy(uid, user_policy)
                logger.info(f"✅ 已强制更新用户 Policy(EnableUserPreferenceAccess=False): {name} ({uid})")
                success_count += 1

            except Exception as e:  # noqa: BLE001
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
        # "0e26758dc85d40488314f9d77d8c9a7d"
    ]

    # 针对失败用户进行重试
    specific_ids = [
        # "ed43223312414d80accfdb722ddddc47"
        "0e26758dc85d40488314f9d77d8c9a7d"
    ]

    try:
        _success, _fail = await sync_all_users_configuration(exclude_user_ids=exclude_ids, specific_user_ids=specific_ids)
    finally:
        # 显式关闭数据库连接池，防止程序退出时报错 "Event loop is closed"
        await engine.dispose()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
