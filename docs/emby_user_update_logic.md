# Emby 用户表更新逻辑

## 核心原则

在更新 `EmbyUserModel` 主表之前，**必须先将当前（旧的）状态保存到 `EmbyUserHistoryModel` 历史表中**。

这意味着历史表记录的是数据变更**之前**的快照，用于审计和回溯。

## 逻辑步骤

1.  **检测变更**：首先对比新数据与当前数据库中的数据，确定是否发生了实质性变更。
2.  **生成备注 (Remark)**：
    *   **历史表备注 (`old_remark`)**：保存当前主表中已有的 `remark`。
    *   **主表备注 (`new_remark`)**：生成本次变更的说明（例如："name 从 A 更新为 B" 或 "系统自动封禁：网页端播放违规"）。
3.  **保存历史快照**：
    *   创建一个新的 `EmbyUserHistoryModel` 实例。
    *   将 `EmbyUserModel` 中的当前字段值（更新前的）复制到历史记录中。
    *   **关键字段映射**：
        *   `user_dto`: 保存旧的 `user_dto`。
        *   `extra_data`: 保存旧的 `extra_data`（建议使用 `copy.deepcopy` 以防引用问题，虽然 JSON 序列化通常是新的对象）。
        *   `remark`: 保存旧的 `remark`。
        *   `action`: 描述本次操作类型（如 `update`, `ban`, `delete`）。
    *   `session.add(history_entry)`
4.  **更新主表**：
    *   修改 `EmbyUserModel` 实例的字段为新值。
    *   `remark` 更新为本次变更说明。
    *   如果修改了 JSON 字段（如 `extra_data`），必须调用 `flag_modified(model, "field_name")`。
    *   `session.add(model)`
5.  **提交事务**：`await session.commit()`

## 代码示例

```python
# 假设 model 是已查询到的 EmbyUserModel 实例

# 1. 保存旧数据快照
history_entry = EmbyUserHistoryModel(
    emby_user_id=model.emby_user_id,
    name=model.name,
    password_hash=model.password_hash,
    date_created=model.date_created,
    last_login_date=model.last_login_date,
    last_activity_date=model.last_activity_date,
    user_dto=model.user_dto,          # 旧的 DTO
    extra_data=model.extra_data,      # 旧的 extra_data
    action="update",                  # 或 "ban"
    remark=model.remark,              # 旧的备注
    # 复制审计字段
    created_at=model.created_at,
    updated_at=model.updated_at,
    created_by=model.created_by,
    updated_by=model.updated_by,
    is_deleted=model.is_deleted,
    deleted_at=model.deleted_at,
    deleted_by=model.deleted_by,
)
session.add(history_entry)

# 2. 更新主表
model.remark = "系统自动封禁：网页端播放违规"
# 确保 extra_data 是字典
if not model.extra_data:
    model.extra_data = {}
# 修改数据
model.extra_data["is_disabled"] = True
# 标记修改
flag_modified(model, "extra_data")

session.add(model)
await session.commit()
```

## 参考实现

请参考 `bot/services/emby_service.py` 中的 `sync_emby_users` 方法逻辑。
