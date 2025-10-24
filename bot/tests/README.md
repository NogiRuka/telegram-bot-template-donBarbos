# Bot测试模块

这个模块提供了测试aiogram和chat_id功能的工具。

## 功能概述

### 1. Chat信息测试类 (`chat_info_test.py`)

`ChatInfoTester` 类提供了以下功能：
- 获取指定chat_id的基本信息
- 获取聊天成员数量
- 获取管理员列表（仅限群组/频道）
- **获取消息详细信息** (新增)
- 批量测试多个chat_id

### 2. Bot命令Handler (`chat_info_handler.py`)

提供以下命令：
- `/chatinfo` - 获取当前聊天的详细信息
- `/testchat <chat_id>` - 测试指定chat_id的信息
- `/myinfo` - 获取发送者的用户信息
- **`/messageinfo <chat_id> <message_id>`** - 获取指定消息的详细信息 (新增)
- `/testhelp` - 显示测试命令帮助

### 3. 独立测试脚本 (`run_chat_test.py`)

可以独立运行的测试脚本，提供：
- Bot自身信息测试
- 特定Chat ID测试
- 交互式测试模式
- **支持消息信息测试** (新增)

## 使用方法

### 方法1：通过Bot命令（推荐）

1. 确保bot在DEBUG模式下运行
2. 在Telegram中向bot发送以下命令：

```
/testhelp                          # 查看帮助
/chatinfo                          # 获取当前聊天信息
/myinfo                            # 获取您的用户信息
/testchat 123456                   # 测试指定chat_id
/messageinfo -1001234567890 123    # 获取群组消息信息 (新增)
/messageinfo @username 456         # 获取用户消息信息 (新增)
```

### 方法2：独立运行测试脚本

```bash
# 在项目根目录下运行
python -m bot.tests.run_chat_test
```

### 方法3：在代码中使用

```python
from bot.tests.chat_info_test import ChatInfoTester

async def test_chat():
    tester = ChatInfoTester()
    
    # 测试单个chat_id
    result = await tester.get_chat_info(123456789)
    print(result)
    
    # 测试消息信息 (新增)
    message_info = await tester.get_message_info(-1001234567890, 123)
    print(message_info)
    
    # 测试多个chat_id
    chat_ids = [123456789, "@username", -1001234567890]
    results = await tester.test_multiple_chats(chat_ids)
    
    await tester.close()
```

## 可获取的信息

### 用户信息
- 用户ID
- 用户名 (@username)
- 名字和姓氏
- 语言代码
- 是否为Bot
- 是否为高级用户
- 个人简介

### 群组/频道信息
- 聊天ID
- 聊天类型 (private, group, supergroup, channel)
- 标题
- 描述
- 成员数量
- 管理员列表
- 权限信息

### 消息信息 (新增)
- 消息ID、发送者信息、发送时间
- 消息内容（文本、媒体、贴纸等）
- 消息实体（链接、提及、格式化等）
- 回复信息、转发信息
- 媒体文件信息（文件ID、大小、尺寸等）
- 编辑时间、媒体组ID
- 受保护内容标识

### 可用的API方法
根据chat类型和bot权限，会显示可用的方法：
- `get_chat` - 获取基本信息
- `get_chat_member_count` - 获取成员数量
- `get_chat_administrators` - 获取管理员列表
- `get_chat_member` - 获取成员信息

## 错误处理

测试工具会处理以下常见错误：
- `TelegramBadRequest` - 无效的chat_id或请求
- `TelegramForbiddenError` - 权限不足
- `TelegramNotFound` - 聊天不存在
- 网络连接错误

## 注意事项

1. **权限限制**：
   - 只能获取bot有权限访问的聊天信息
   - 私聊需要用户先与bot对话
   - 群组需要bot是成员
   - 频道需要bot是管理员
   - **获取消息信息需要转发权限** (新增)

2. **调试模式**：
   - Bot命令仅在DEBUG模式下可用
   - 生产环境不会加载测试路由

3. **安全性**：
   - 不要在生产环境中启用测试功能
   - 测试命令可能暴露敏感信息
   - **消息信息可能包含敏感内容，请谨慎处理** (新增)

## 配置要求

确保在 `.env` 文件中配置了：
```
BOT_TOKEN=your_bot_token_here
DEBUG=true  # 启用调试模式以使用bot命令
```

## 示例输出

### 成功获取用户信息
```json
{
  "success": true,
  "chat_id": 123456789,
  "chat_info": {
    "id": 123456789,
    "type": "private",
    "username": "example_user",
    "first_name": "John",
    "last_name": "Doe",
    "bio": "Software Developer"
  },
  "available_methods": ["get_chat"]
}
```

### 成功获取群组信息
```json
{
  "success": true,
  "chat_id": -1001234567890,
  "chat_info": {
    "id": -1001234567890,
    "type": "supergroup",
    "title": "Test Group",
    "description": "A test group for bot development",
    "username": "test_group"
  },
  "member_count": 150,
  "administrators": [...],
  "available_methods": ["get_chat", "get_chat_member_count", "get_chat_administrators"]
}
```

### 错误情况
```json
{
  "success": false,
  "chat_id": 999999999,
  "error": "Chat not found",
  "available_methods": []
}
```