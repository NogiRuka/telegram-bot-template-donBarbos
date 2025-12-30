import asyncio
import os
import sys

from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.append(os.getcwd())

import contextlib

from bot.database.database import engine, sessionmaker
from bot.services.emby_service import save_all_emby_devices


async def main() -> None:
    logger.info("开始同步 Emby 设备...")
    try:
        async with sessionmaker() as session:
            try:
                count = await save_all_emby_devices(session)
                logger.info(f"同步完成。总设备数: {count}")
            except Exception as e:
                logger.error(f"同步失败: {e}")
                import traceback
                traceback.print_exc()
    finally:
        # 显式关闭数据库连接池，防止 Event loop closed 错误
        await engine.dispose()

if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
