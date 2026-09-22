# Emby 用户更新逻辑文档

本文档详细说明了本项目中 Emby 用户数据的更新逻辑，特别是涉及主表 `emby_users` 和历史表 `emby_user_history` 的交互流程。

## 核心原则

1.  **快照优先 (Snapshot-First)**: 在更新主表数据之前，必须先将当前的（旧的）状态保存到历史表中。
2.  **完整性 (Completeness)**: 历史记录必须包含更新前的所有关键字段，以便回溯。
3.  **原子性 (Atomicity)**: 历史记录的插入和主表的更新必须在同一个数据库事务中完成。

## 数据模型

-   **主表 (`EmbyUserModel`)**: 存储当前最新的 Emby 用户状态。
-   **历史表 (`EmbyUserHistoryModel`)**: 存储 Emby 用户状态变更的历史快照。

## 更新流程

更新逻辑封装在 `bot.services.emby_update_helper.detect_and_update_emby_user` 函数中。

### 1. 检测变更

首先比较新传入的 `UserDto` (来自 Emby API) 和数据库中现有的 `user_dto` 字段。

-   如果两者一致且未指定 `force_update=True`，则跳过更新。
-   如果两者不一致，或者指定了 `force_update=True`，则执行更新流程。

### 2. 创建历史快照

在修改主表之前，创建一个 `EmbyUserHistoryModel` 实例，记录以下信息：

-   `emby_user_id`: 关联的 Emby 用户 ID
-   `name`: 更新前的用户名
-   `user_dto`: 更新前的完整 UserDto JSON
-   `date_created`, `last_login_date`, `last_activity_date`: 更新前的时间字段
-   `remark`: 更新前的备注
-   `action`: 操作类型（默认为 "update"，如果有 `extra_remark` 则可能为 "system_update" 等）

### 3. 更新主表

在历史记录保存后，更新主表 `EmbyUserModel` 的字段：

-   `user_dto`: 更新为新的 UserDto
-   `name`: 从新 UserDto 中提取
-   `date_created`, `last_login_date`, `last_activity_date`: 从新 UserDto 中提取并格式化
-   `remark`: 更新为新的备注（如果有）

### 4. 提交事务

将历史记录的插入和主表的更新作为一个事务提交到数据库。

## 代码示例

```python
from bot.services.emby_update_helper import detect_and_update_emby_user

# 假设 session, emby_user (Model), new_user_dto (Dict) 已存在

# 调用通用更新函数
detect_and_update_emby_user(
    model=emby_user,
    new_user_dto=new_user_dto,
    session=session,
    force_update=False,  # 可选：强制更新
    extra_remark="管理员手动更新"  # 可选：附加说明
)

# 提交事务
await session.commit()
```

## 特殊场景：封禁用户

当封禁用户时，流程如下：

1.  调用 Emby API 禁用用户 (`emby_client.disable_user`).
2.  获取最新的 UserDto (包含 `IsDisabled: true`).
3.  调用 `detect_and_update_emby_user` 强制更新本地数据，记录封禁快照。
4.  额外更新 `extra_data` 字段，记录 `is_disabled`, `disabled_reason`, `disabled_at`, `disabled_by` 等信息。

```python
# 示例：封禁逻辑
detect_and_update_emby_user(
    model=emby_user,
    new_user_dto=new_user_dto,
    session=session,
    force_update=True,
    extra_remark="系统自动封禁"
)

emby_user.extra_data["is_disabled"] = True
# ... 其他 extra_data 更新 ...
flag_modified(emby_user, "extra_data")
```
