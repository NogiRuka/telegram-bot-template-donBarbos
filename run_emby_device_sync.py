import asyncio
import sys
import os
from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.append(os.getcwd())

from bot.database.database import sessionmaker
from bot.services.emby_service import save_all_emby_devices

async def main():
    logger.info("Starting Emby device sync...")
    async with sessionmaker() as session:
        try:
            count = await save_all_emby_devices(session)
            logger.info(f"Sync completed. Total devices: {count}")
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
