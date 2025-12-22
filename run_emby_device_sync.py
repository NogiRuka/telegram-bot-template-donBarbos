import asyncio
import sys
import os
from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.append(os.getcwd())

from bot.database.database import sessionmaker
from bot.services.emby_service import save_all_emby_devices

async def main():
    logger.info("开始同步 Emby 设备...")
    async with sessionmaker() as session:
        try:
            count = await save_all_emby_devices(session)
            logger.info(f"同步完成。总设备数: {count}")
        except Exception as e:
            logger.error(f"同步失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
