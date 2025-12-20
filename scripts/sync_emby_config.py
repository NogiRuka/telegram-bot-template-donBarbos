import asyncio
import sys
from pathlib import Path

# Add project root to path
# Use parent of parent because this script is in scripts/ folder
sys.path.append(str(Path(__file__).parent.parent))

import contextlib

from loguru import logger

from bot.services.emby_service import sync_all_users_configuration


async def main() -> None:
    logger.info("开始执行 Emby 用户配置批量同步...")

    # 用户指定的排除 ID

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
