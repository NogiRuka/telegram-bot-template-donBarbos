# Emby API 测试命令

## 快速测试命令

### 1. 基础测试
```bash
# 运行完整的API测试
python test_emby_api.py

# 快速测试（需要修改脚本中的ITEM_ID）
python test_emby_quick.py
```

### 2. 交互式测试
```python
# 在Python交互环境中测试
import asyncio
from bot.core.emby import EmbyClient
from bot.core.config import settings

async def test():
    client = EmbyClient(
        base_url=settings.EMBY_BASE_URL,
        api_key=settings.EMBY_API_KEY,
        user_id=settings.EMBY_ADMIN_ID
    )
    
    # 替换为实际的项目ID
    result = await client.get_item(settings.EMBY_ADMIN_ID, "YOUR_ITEM_ID")
    print(result)
    await client.close()

# 运行测试
asyncio.run(test())
```

## 获取项目ID的方法

1. **通过Emby Web界面**
   - 打开Emby Web界面
   - 点击任意一个项目（电影、电视剧等）
   - 查看浏览器地址栏中的URL
   - 找到`id=xxx`参数，这就是项目ID
   
   例如：`http://your-emby-server/web/index.html#!/item?id=12345`
   项目ID就是：`12345`

2. **通过API获取项目列表**
   ```python
   # 需要先获取用户库，然后遍历项目
   # 这需要额外的API调用，建议直接使用Web界面获取ID
   ```

## 测试参数配置

确保在`.env`文件中配置了以下参数：
```env
EMBY_BASE_URL=http://your-emby-server:8096
EMBY_API_KEY=your-api-key
EMBY_ADMIN_ID=your-admin-user-id
```

## 常见错误处理

1. **连接错误**
   - 检查EMBY_BASE_URL是否正确
   - 确保Emby服务器可访问

2. **认证错误**
   - 检查EMBY_API_KEY是否有效
   - 确认用户ID存在且有效

3. **项目不存在**
   - 确认项目ID是否正确
   - 检查项目是否被删除或移动

## 测试成功标志

✅ 成功时应该能看到：
- 项目名称
- 项目类型（Movie、Series等）
- 项目详细信息

❌ 失败时可能看到：
- 空数据（{}）
- 错误信息
- 异常抛出