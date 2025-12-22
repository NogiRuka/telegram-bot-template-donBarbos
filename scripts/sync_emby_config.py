import asyncio
import sys
from pathlib import Path

# Add project root to path
# Use parent of parent because this script is in scripts/ folder
sys.path.append(str(Path(__file__).parent.parent))

import contextlib

from loguru import logger

from bot.core.config import settings
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

    # 获取目标用户列表
    all_users = []
    if specific_user_ids:
        # 指定了用户ID列表，直接构造用户对象列表（需获取Name以便日志显示）
        for uid in specific_user_ids:
            try:
                # 尝试获取用户信息以获得正确的 Name
                u = await client.get_user(uid)
                if u:
                    all_users.append(u)
                else:
                    # 获取失败或为空，构造一个只有 ID 的对象
                    all_users.append({"Id": uid, "Name": "Unknown"})
            except Exception:
                # 获取失败，构造一个只有 ID 的对象
                all_users.append({"Id": uid, "Name": "Unknown"})
    else:
        # 未指定用户，拉取所有用户
        try:
            start_index = 0
            page_limit = 200
            while True:
                items, total = await client.get_users(start_index=start_index, limit=page_limit)
                if not items:
                    break
                all_users.extend(items)
                start_index += len(items)
                if len(all_users) >= total or len(items) < page_limit:
                    break
        except Exception as e:
            logger.error(f"❌ 获取用户列表失败: {e}")
            return 0, 0

    # 准备排除列表
    skips = set(exclude_user_ids or [])
    skips.add(tid)  # 排除模板用户自己

    success_count = 0
    fail_count = 0

    logger.info(f"🔄 开始批量同步 Emby 用户配置, 模板用户: {tid}, 目标用户数: {len(all_users)}")

    for user in all_users:
        uid = user.get("Id")
        name = user.get("Name")
        if not uid:
            continue

        if uid in skips and not specific_user_ids:
             # 只有在非指定模式下才检查排除列表
             # 如果明确指定了 specific_user_ids，则即使在 exclude 中也应该执行（或者看逻辑，通常 specific 优先级更高）
             # 这里保持 specific 优先级更高，不检查 skip
             pass
        elif uid in skips:
             logger.debug(f"⏭️ 跳过用户: {name} ({uid})")
             continue

        try:
            # 更新 Configuration
            await client.update_user_configuration(uid, template_config)
            # 更新 Policy
            await client.update_user_policy(uid, template_policy)
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
        # "user_id_here",
    ]

    # 针对失败用户进行重试
    specific_ids = [
        "20dc095abfb14ef98559e4a9b4d7ac75"
    ]

    # success, fail = await sync_all_users_configuration(exclude_user_ids=exclude_ids)

    # 只处理失败的用户
    _success, _fail = await sync_all_users_configuration(specific_user_ids=specific_ids)


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
