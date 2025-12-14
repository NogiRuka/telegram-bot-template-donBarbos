import asyncio
import sys
from pathlib import Path

# Add project root to path
# Use parent of parent because this script is in scripts/ folder
sys.path.append(str(Path(__file__).parent.parent))

from bot.services.emby_service import sync_all_users_configuration
from loguru import logger

async def main():
    logger.info("开始执行 Emby 用户配置批量同步...")
    
    # 用户指定的排除 ID
    exclude_ids = [
        "945e1aa74d964da183b3e6a0f0075d6f",
        "52588e7dbcbe4ea7a575dfe86a7f4a28"
    ]
    
    # 针对失败用户进行重试
    specific_ids = [
        "20dc095abfb14ef98559e4a9b4d7ac75"
    ]

    # success, fail = await sync_all_users_configuration(exclude_user_ids=exclude_ids)
    
    # 只处理失败的用户
    success, fail = await sync_all_users_configuration(specific_user_ids=specific_ids)
    
    print(f"\n===========================================")
    print(f"执行结果: 成功 {success} 个, 失败 {fail} 个")
    print(f"===========================================\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
