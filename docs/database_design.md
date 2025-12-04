# 数据库设计文档

## 概述

**数据库**: MySQL 8.0+  
**字符集**: utf8mb4  
**排序规则**: utf8mb4_unicode_ci  

---

## 1. 用户表 (users)

存储 Telegram 用户基本信息（与 aiogram User 对应）。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | BIGINT | - | NO | - | PK | Telegram 用户 ID |
| is_bot | TINYINT | 1 | NO | 0 | - | 是否为机器人 |
| first_name | VARCHAR | 255 | NO | - | - | 名字 |
| last_name | VARCHAR | 255 | YES | NULL | - | 姓氏 |
| username | VARCHAR | 255 | YES | NULL | IDX | 用户名 |
| language_code | VARCHAR | 32 | YES | NULL | - | 语言代码 |
| is_premium | TINYINT | 1 | YES | NULL | - | 是否 Premium 用户 |
| added_to_attachment_menu | TINYINT | 1 | YES | NULL | - | 是否加入附件菜单 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | IDX | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | IDX | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | IDX | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | IDX | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | IDX | 删除者ID |

```sql
CREATE TABLE users (
    id BIGINT NOT NULL COMMENT 'Telegram 用户 ID',
    is_bot TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否为机器人',
    first_name VARCHAR(255) NOT NULL COMMENT '名字',
    last_name VARCHAR(255) COMMENT '姓氏',
    username VARCHAR(255) COMMENT '用户名',
    language_code VARCHAR(32) COMMENT '语言代码',
    is_premium TINYINT(1) COMMENT '是否 Premium 用户',
    added_to_attachment_menu TINYINT(1) COMMENT '是否加入附件菜单',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (id),
    INDEX idx_users_username (username),
    INDEX idx_users_created_at (created_at),
    INDEX idx_users_updated_at (updated_at),
    INDEX idx_users_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 2. 消息表 (messages)

存储用户消息记录。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | INT | - | NO | AUTO | PK | 记录ID |
| message_id | BIGINT | - | NO | - | IDX | 消息ID |
| user_id | BIGINT | - | NO | - | IDX | 用户ID |
| chat_id | BIGINT | - | NO | - | IDX | 聊天ID |
| message_type | ENUM | - | NO | 'text' | IDX | 消息类型 |
| content | TEXT | - | YES | NULL | - | 内容 |
| file_id | VARCHAR | 255 | YES | NULL | - | 文件ID |
| file_size | INT | - | YES | NULL | - | 文件大小 |
| reply_to_message_id | BIGINT | - | YES | NULL | IDX | 回复消息ID |
| forward_from_user_id | BIGINT | - | YES | NULL | IDX | 转发用户ID |
| forward_from_chat_id | BIGINT | - | YES | NULL | IDX | 转发聊天ID |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | IDX | 记录者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |

```sql
CREATE TABLE messages (
    id INT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
    message_id BIGINT NOT NULL COMMENT '消息ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    chat_id BIGINT NOT NULL COMMENT '聊天ID',
    message_type ENUM('text','photo','video','audio','voice','document','sticker','animation','location','contact','poll','dice','game','other') NOT NULL DEFAULT 'text' COMMENT '消息类型',
    content TEXT COMMENT '内容',
    file_id VARCHAR(255) COMMENT '文件ID',
    file_size INT COMMENT '文件大小',
    reply_to_message_id BIGINT COMMENT '回复消息ID',
    forward_from_user_id BIGINT COMMENT '转发用户ID',
    forward_from_chat_id BIGINT COMMENT '转发聊天ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '记录者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX ix_messages_message_id (message_id),
    INDEX ix_messages_user_id (user_id),
    INDEX ix_messages_chat_id (chat_id),
    INDEX ix_messages_message_type (message_type),
    INDEX ix_messages_created_at (created_at),
    INDEX ix_messages_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 3. 用户状态表 (user_states)

存储用户对话状态。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| user_id | BIGINT | - | NO | - | PK | 用户ID |
| state | VARCHAR | 255 | YES | NULL | IDX | 状态 |
| data | JSON | - | YES | NULL | - | 状态数据 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | IDX | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | IDX | 更新者ID |

```sql
CREATE TABLE user_states (
    user_id BIGINT NOT NULL COMMENT '用户ID',
    state VARCHAR(255) COMMENT '状态',
    data JSON COMMENT '状态数据',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    PRIMARY KEY (user_id),
    INDEX ix_user_states_state (state),
    INDEX ix_user_states_created_at (created_at),
    INDEX ix_user_states_created_by (created_by),
    INDEX ix_user_states_updated_by (updated_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 4. 配置表 (configs)

存储系统配置。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| key | VARCHAR | 255 | NO | - | PK | 配置键 |
| value | TEXT | - | YES | NULL | - | 配置值 |
| config_type | ENUM | - | NO | 'string' | IDX | 类型 |
| default_value | TEXT | - | YES | NULL | - | 默认值 |
| description | TEXT | - | YES | NULL | - | 描述 |
| category | VARCHAR | 100 | YES | NULL | IDX | 分类 |
| is_public | TINYINT | 1 | NO | 0 | IDX | 公开 |
| is_editable | TINYINT | 1 | NO | 1 | IDX | 可编辑 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | IDX | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | IDX | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | IDX | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | IDX | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | IDX | 删除者ID |

```sql
CREATE TABLE configs (
    `key` VARCHAR(255) NOT NULL COMMENT '配置键',
    value TEXT COMMENT '配置值',
    config_type ENUM('string','integer','float','boolean','json','text','list','dict') NOT NULL DEFAULT 'string' COMMENT '类型',
    default_value TEXT COMMENT '默认值',
    description TEXT COMMENT '描述',
    category VARCHAR(100) COMMENT '分类',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (`key`),
    INDEX ix_configs_config_type (config_type),
    INDEX ix_configs_category (category),
    INDEX ix_configs_is_public (is_public),
    INDEX ix_configs_is_editable (is_editable),
    INDEX ix_configs_is_deleted (is_deleted),
    INDEX ix_configs_created_by (created_by),
    INDEX ix_configs_updated_by (updated_by),
    INDEX ix_configs_deleted_by (deleted_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 5. 审计日志表 (audit_logs)

记录操作日志。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | INT | - | NO | AUTO | PK | 日志ID |
| action_type | ENUM | - | NO | - | IDX | 操作类型 |
| user_id | BIGINT | - | YES | NULL | IDX | 目标用户ID |
| operator_id | BIGINT | - | YES | NULL | IDX | 操作者ID |
| operator_name | VARCHAR | 255 | YES | NULL | IDX | 操作者名称 |
| target_type | VARCHAR | 100 | YES | NULL | IDX | 目标类型 |
| target_id | VARCHAR | 255 | YES | NULL | IDX | 目标ID |
| description | TEXT | - | YES | NULL | - | 操作描述 |
| details | JSON | - | YES | NULL | - | 详细信息 |
| ip_address | VARCHAR | 45 | YES | NULL | IDX | IP地址 |
| user_agent | TEXT | - | YES | NULL | - | 用户代理 |
| session_id | VARCHAR | 255 | YES | NULL | IDX | 会话ID |
| is_success | TINYINT | 1 | NO | 1 | IDX | 操作成功 |
| error_message | TEXT | - | YES | NULL | - | 错误信息 |
| duration_ms | INT | - | YES | NULL | IDX | 耗时(ms) |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | IDX | 记录者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |

```sql
CREATE TABLE audit_logs (
    id INT NOT NULL AUTO_INCREMENT COMMENT '日志ID',
    action_type ENUM('user_create','user_update','user_delete','user_block','user_unblock','message_send','config_update','admin_action','other') NOT NULL COMMENT '操作类型',
    user_id BIGINT COMMENT '目标用户ID',
    operator_id BIGINT COMMENT '操作者ID',
    operator_name VARCHAR(255) COMMENT '操作者名称',
    target_type VARCHAR(100) COMMENT '目标类型',
    target_id VARCHAR(255) COMMENT '目标ID',
    description TEXT COMMENT '操作描述',
    details JSON COMMENT '详细信息',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    session_id VARCHAR(255) COMMENT '会话ID',
    is_success TINYINT(1) NOT NULL DEFAULT 1 COMMENT '操作成功',
    error_message TEXT COMMENT '错误信息',
    duration_ms INT COMMENT '耗时(ms)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '记录者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX ix_audit_logs_action_type (action_type),
    INDEX ix_audit_logs_user_id (user_id),
    INDEX ix_audit_logs_operator_id (operator_id),
    INDEX ix_audit_logs_target_type (target_type),
    INDEX ix_audit_logs_ip_address (ip_address),
    INDEX ix_audit_logs_is_success (is_success),
    INDEX ix_audit_logs_created_at (created_at),
    INDEX ix_audit_logs_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 6. 统计表 (statistics)

存储统计数据。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | INT | - | NO | AUTO | PK | 统计ID |
| statistic_type | ENUM | - | NO | - | IDX | 统计类型 |
| key | VARCHAR | 255 | NO | - | IDX | 统计键 |
| value | BIGINT | - | NO | 0 | IDX | 统计值 |
| date | DATE | - | NO | - | IDX | 日期 |
| hour | TINYINT | - | YES | NULL | IDX | 小时 |
| metadata | JSON | - | YES | NULL | - | 元数据 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | IDX | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | IDX | 更新者ID |

```sql
CREATE TABLE statistics (
    id INT NOT NULL AUTO_INCREMENT COMMENT '统计ID',
    statistic_type ENUM('daily','hourly','monthly','yearly','total','custom') NOT NULL COMMENT '统计类型',
    `key` VARCHAR(255) NOT NULL COMMENT '统计键',
    value BIGINT NOT NULL DEFAULT 0 COMMENT '统计值',
    date DATE NOT NULL COMMENT '日期',
    hour TINYINT COMMENT '小时',
    metadata JSON COMMENT '元数据',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    PRIMARY KEY (id),
    INDEX ix_statistics_statistic_type (statistic_type),
    INDEX ix_statistics_key (`key`),
    INDEX ix_statistics_value (value),
    INDEX ix_statistics_date (date),
    INDEX ix_statistics_hour (hour),
    INDEX ix_statistics_created_by (created_by),
    INDEX ix_statistics_updated_by (updated_by),
    UNIQUE INDEX idx_statistics_unique (statistic_type, `key`, date, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 7. 用户扩展表 (user_extend)

存储用户的扩展信息，如角色权限、电话、简介等（与 users 表分离）。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| user_id | BIGINT | - | NO | - | PK,FK | 用户ID（关联 users.id） |
| role | ENUM | - | NO | 'user' | IDX | 用户角色（user/admin/owner） |
| phone | VARCHAR | 32 | YES | NULL | - | 电话号码 |
| bio | VARCHAR | 512 | YES | NULL | - | 用户简介 |
| emby_user_id | VARCHAR | 64 | YES | NULL | IDX | Emby 用户ID |
| ip_list | JSON | - | YES | NULL | - | 访问过的 IP 数组 |
| last_interaction_at | DATETIME | - | YES | NULL | IDX | 最后与机器人交互的时间 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | - | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | - | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | IDX | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | - | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | - | 删除者ID |

```sql
CREATE TABLE user_extend (
    user_id BIGINT NOT NULL COMMENT '用户ID',
    role ENUM('user','admin','owner') NOT NULL DEFAULT 'user' COMMENT '用户角色权限',
    phone VARCHAR(32) COMMENT '电话号码',
    bio VARCHAR(512) COMMENT '用户简介',
    emby_user_id VARCHAR(64) COMMENT 'Emby 用户ID',
    ip_list JSON COMMENT '访问过的IP数组',
    last_interaction_at DATETIME COMMENT '最后与机器人交互的时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (user_id),
    INDEX idx_user_extend_role (role),
    INDEX idx_user_extend_emby_user_id (emby_user_id),
    INDEX idx_user_extend_last_interaction (last_interaction_at),
    CONSTRAINT fk_user_extend_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 8. 用户历史表 (user_history)

存储用户信息的历史快照，用于追踪用户信息变更。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| history_id | BIGINT | - | NO | AUTO | PK | 主键ID |
| user_id | BIGINT | - | NO | - | IDX | 用户ID |
| is_bot | TINYINT | 1 | NO | 0 | - | 是否机器人 |
| first_name | VARCHAR | 255 | NO | - | - | 名字 |
| last_name | VARCHAR | 255 | YES | NULL | - | 姓氏 |
| username | VARCHAR | 255 | YES | NULL | - | 用户名 |
| language_code | VARCHAR | 32 | YES | NULL | - | 语言代码 |
| is_premium | TINYINT | 1 | YES | NULL | - | 是否 Premium 用户 |
| added_to_attachment_menu | TINYINT | 1 | YES | NULL | - | 是否加入附件菜单 |
| snapshot_at | DATETIME | - | NO | NOW() | IDX | 快照时间 |
| created_at | DATETIME | - | NO | NOW() | - | 创建时间 |
| created_by | BIGINT | - | YES | NULL | - | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | - | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | - | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | - | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | - | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | - | 删除者ID |

```sql
CREATE TABLE user_history (
    history_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    is_bot TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否机器人',
    first_name VARCHAR(255) NOT NULL COMMENT '名字',
    last_name VARCHAR(255) COMMENT '姓氏',
    username VARCHAR(255) COMMENT '用户名',
    language_code VARCHAR(32) COMMENT '语言代码',
    is_premium TINYINT(1) COMMENT '是否 Premium 用户',
    added_to_attachment_menu TINYINT(1) COMMENT '是否加入附件菜单',
    snapshot_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '快照时间',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (history_id),
    INDEX idx_user_history_user_id (user_id),
    INDEX idx_user_history_user_snapshot (user_id, snapshot_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 9. 群组配置表 (group_configs)

存储群组的消息保存配置和相关设置。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | INT | - | NO | AUTO | PK | 群组配置ID |
| chat_id | BIGINT | - | NO | - | UNI | 聊天ID |
| chat_title | VARCHAR | 255 | YES | NULL | - | 群组标题 |
| chat_username | VARCHAR | 100 | YES | NULL | IDX | 群组用户名 |
| group_type | ENUM | - | NO | - | IDX | 群组类型 |
| is_message_save_enabled | TINYINT | 1 | NO | 0 | IDX | 是否启用消息保存 |
| message_save_mode | ENUM | - | NO | 'disabled' | IDX | 消息保存模式 |
| save_start_date | DATETIME | - | YES | NULL | - | 保存开始时间 |
| save_end_date | DATETIME | - | YES | NULL | - | 保存结束时间 |
| max_messages_per_day | INT | - | YES | NULL | - | 每日最大消息数 |
| max_file_size_mb | INT | - | YES | NULL | - | 最大文件大小(MB) |
| save_text_messages | TINYINT | 1 | NO | 1 | - | 保存文本消息 |
| save_media_messages | TINYINT | 1 | NO | 1 | - | 保存媒体消息 |
| save_forwarded_messages | TINYINT | 1 | NO | 1 | - | 保存转发消息 |
| save_reply_messages | TINYINT | 1 | NO | 1 | - | 保存回复消息 |
| save_bot_messages | TINYINT | 1 | NO | 0 | - | 保存机器人消息 |
| include_keywords | TEXT | - | YES | NULL | - | 包含关键词(JSON) |
| exclude_keywords | TEXT | - | YES | NULL | - | 排除关键词(JSON) |
| total_messages_saved | INT | - | NO | 0 | - | 已保存消息总数 |
| last_message_date | DATETIME | - | YES | NULL | IDX | 最后消息时间 |
| configured_by_user_id | BIGINT | - | YES | NULL | - | 配置者用户ID |
| notes | TEXT | - | YES | NULL | - | 备注信息 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | - | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | - | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | IDX | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | - | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | - | 删除者ID |

```sql
CREATE TABLE group_configs (
    id INT NOT NULL AUTO_INCREMENT COMMENT '群组配置ID',
    chat_id BIGINT NOT NULL COMMENT '聊天ID',
    chat_title VARCHAR(255) COMMENT '群组标题',
    chat_username VARCHAR(100) COMMENT '群组用户名',
    group_type ENUM('group','supergroup','channel') NOT NULL COMMENT '群组类型',
    is_message_save_enabled TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否启用消息保存',
    message_save_mode ENUM('all','text_only','media_only','important_only','disabled') NOT NULL DEFAULT 'disabled' COMMENT '消息保存模式',
    save_start_date DATETIME COMMENT '保存开始时间',
    save_end_date DATETIME COMMENT '保存结束时间',
    max_messages_per_day INT COMMENT '每日最大消息数',
    max_file_size_mb INT COMMENT '最大文件大小(MB)',
    save_text_messages TINYINT(1) NOT NULL DEFAULT 1 COMMENT '保存文本消息',
    save_media_messages TINYINT(1) NOT NULL DEFAULT 1 COMMENT '保存媒体消息',
    save_forwarded_messages TINYINT(1) NOT NULL DEFAULT 1 COMMENT '保存转发消息',
    save_reply_messages TINYINT(1) NOT NULL DEFAULT 1 COMMENT '保存回复消息',
    save_bot_messages TINYINT(1) NOT NULL DEFAULT 0 COMMENT '保存机器人消息',
    include_keywords TEXT COMMENT '包含关键词(JSON)',
    exclude_keywords TEXT COMMENT '排除关键词(JSON)',
    total_messages_saved INT NOT NULL DEFAULT 0 COMMENT '已保存消息总数',
    last_message_date DATETIME COMMENT '最后消息时间',
    configured_by_user_id BIGINT COMMENT '配置者用户ID',
    notes TEXT COMMENT '备注信息',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (id),
    UNIQUE INDEX idx_group_configs_chat_id (chat_id),
    INDEX idx_group_configs_username (chat_username),
    INDEX idx_group_configs_type (group_type),
    INDEX idx_group_configs_enabled (is_message_save_enabled),
    INDEX idx_group_configs_mode (message_save_mode),
    INDEX idx_group_configs_last_message (last_message_date),
    INDEX idx_group_configs_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 10. Emby 用户表 (emby_users)

存储从 Emby 创建/同步的用户基本信息。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | INT | - | NO | AUTO | PK | 自增主键 |
| emby_user_id | VARCHAR | 64 | NO | - | UNI | Emby 用户ID |
| name | VARCHAR | 255 | NO | - | IDX | Emby 用户名 |
| user_dto | JSON | - | YES | NULL | - | Emby 返回的 UserDto JSON |
| password_hash | VARCHAR | 128 | YES | NULL | - | 密码哈希 (bcrypt) |
| date_created | DATETIME | - | YES | NULL | - | 用户创建时间(来自 Emby) |
| last_login_date | DATETIME | - | YES | NULL | - | 最后登录时间(来自 Emby) |
| last_activity_date | DATETIME | - | YES | NULL | - | 最后活动时间(来自 Emby) |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | - | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | - | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | IDX | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | - | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | - | 删除者ID |

```sql
CREATE TABLE emby_users (
    id INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    emby_user_id VARCHAR(64) NOT NULL COMMENT 'Emby 用户ID(字符串)',
    name VARCHAR(255) NOT NULL COMMENT 'Emby 用户名',
    user_dto JSON COMMENT 'Emby 返回的 UserDto JSON 对象',
    password_hash VARCHAR(128) COMMENT '密码哈希 (bcrypt)',
    date_created DATETIME COMMENT '用户创建时间(来自 Emby)',
    last_login_date DATETIME COMMENT '最后登录时间(来自 Emby)',
    last_activity_date DATETIME COMMENT '最后活动时间(来自 Emby)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (id),
    UNIQUE INDEX idx_emby_users_emby_user_id (emby_user_id),
    INDEX idx_emby_users_name (name),
    INDEX idx_emby_users_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 11. Emby 用户历史表 (emby_user_history)

记录 Emby 用户创建、更新、删除等历史快照。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | INT | - | NO | AUTO | PK | 自增主键 |
| emby_user_id | VARCHAR | 64 | NO | - | IDX | Emby 用户ID |
| name | VARCHAR | 255 | NO | - | IDX | Emby 用户名 |
| user_dto | JSON | - | YES | NULL | - | UserDto JSON 快照 |
| password_hash | VARCHAR | 128 | YES | NULL | - | 密码哈希 |
| date_created | DATETIME | - | YES | NULL | - | 用户创建时间快照 |
| last_login_date | DATETIME | - | YES | NULL | - | 最后登录时间快照 |
| last_activity_date | DATETIME | - | YES | NULL | - | 最后活动时间快照 |
| action | VARCHAR | 32 | NO | - | IDX | 动作类型(create/update/delete) |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | - | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | - | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | - | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | - | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | - | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | - | 删除者ID |

```sql
CREATE TABLE emby_user_history (
    id INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    emby_user_id VARCHAR(64) NOT NULL COMMENT 'Emby 用户ID(字符串)',
    name VARCHAR(255) NOT NULL COMMENT 'Emby 用户名',
    user_dto JSON COMMENT 'UserDto JSON 快照',
    password_hash VARCHAR(128) COMMENT '密码哈希 (bcrypt)',
    date_created DATETIME COMMENT '用户创建时间快照',
    last_login_date DATETIME COMMENT '最后登录时间快照',
    last_activity_date DATETIME COMMENT '最后活动时间快照',
    action VARCHAR(32) NOT NULL COMMENT '动作类型(create/update/delete)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (id),
    INDEX idx_emby_user_history_emby_user_id (emby_user_id),
    INDEX idx_emby_user_history_name (name),
    INDEX idx_emby_user_history_action (action),
    INDEX idx_emby_user_history_user_action (emby_user_id, action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 12. 一言表 (hitokoto)

存储从 Hitokoto 接口获取的一言信息。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | INT | - | NO | AUTO | PK | 自增主键 |
| hitokoto_id | INT | - | YES | NULL | IDX | 一言标识 |
| hitokoto | TEXT | - | NO | - | - | 一言正文 |
| type | VARCHAR | 2 | YES | NULL | IDX | 类型(a-动画/b-漫画/c-游戏等) |
| from | VARCHAR | 255 | YES | NULL | - | 一言的出处 |
| from_who | VARCHAR | 255 | YES | NULL | - | 一言的作者 |
| creator | VARCHAR | 255 | YES | NULL | - | 添加者 |
| creator_uid | INT | - | YES | NULL | - | 添加者用户标识 |
| reviewer | INT | - | YES | NULL | - | 审核员标识 |
| uuid | VARCHAR | 64 | NO | - | UNI | 一言唯一标识 |
| commit_from | VARCHAR | 64 | YES | NULL | - | 提交方式 |
| source_created_at | VARCHAR | 64 | YES | NULL | - | 来源添加时间 |
| length | INT | - | YES | NULL | - | 句子长度 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | - | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | - | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | - | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | - | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | - | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | - | 删除者ID |

```sql
CREATE TABLE hitokoto (
    id INT NOT NULL AUTO_INCREMENT COMMENT '自增主键',
    hitokoto_id INT COMMENT '一言标识',
    hitokoto TEXT NOT NULL COMMENT '一言正文(utf-8编码)',
    type VARCHAR(2) COMMENT '类型(a-动画 b-漫画 c-游戏 d-文学 e-原创 f-来自网络 g-其他 h-影视 i-诗词 j-网易云 k-哲学 l-抖机灵)',
    `from` VARCHAR(255) COMMENT '一言的出处',
    from_who VARCHAR(255) COMMENT '一言的作者',
    creator VARCHAR(255) COMMENT '添加者',
    creator_uid INT COMMENT '添加者用户标识',
    reviewer INT COMMENT '审核员标识',
    uuid VARCHAR(64) NOT NULL COMMENT '一言唯一标识',
    commit_from VARCHAR(64) COMMENT '提交方式',
    source_created_at VARCHAR(64) COMMENT '来源添加时间',
    length INT COMMENT '句子长度',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (id),
    INDEX idx_hitokoto_id (hitokoto_id),
    INDEX idx_hitokoto_type (type),
    UNIQUE INDEX idx_hitokoto_uuid (uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 13. 外键约束

```sql
-- 消息关联
ALTER TABLE messages ADD CONSTRAINT fk_messages_user_id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 用户状态关联
ALTER TABLE user_states ADD CONSTRAINT fk_user_states_user_id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 用户扩展关联
ALTER TABLE user_extend ADD CONSTRAINT fk_user_extend_user_id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 审计日志关联
ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_user_id
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
```

---

## 14. 初始化脚本

```sql
-- 创建数据库
CREATE DATABASE telegram_bot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE telegram_bot;

-- 设置时区
SET time_zone = '+00:00';

-- 依次执行上述建表语句
-- 最后添加外键约束
```

---

## 15. 字段含义说明

### 操作者字段说明

| 字段名 | 含义 | 使用场景 |
|--------|------|----------|
| **created_by** | 创建者ID | 记录谁创建了这条记录（管理员ID、系统ID等） |
| **updated_by** | 更新者ID | 记录谁最后更新了这条记录 |
| **deleted_by** | 删除者ID | 记录谁执行了软删除操作 |
| **operator_id** | 操作者ID | 审计日志中记录具体执行操作的用户ID |
| **operator_name** | 操作者名称 | 审计日志中记录操作者的显示名称 |
| **created_by (messages)** | 记录者ID | 消息表中记录是谁记录了这条消息（通常是系统） |
| **created_by (audit_logs)** | 记录者ID | 审计日志中记录是谁创建了这条日志记录 |

### 特殊说明

- **系统操作**: 当系统自动执行操作时，相关字段可以设置为特殊值（如 -1 表示系统）
- **用户自助操作**: 用户自己的操作，created_by/updated_by 设置为用户自己的ID
- **管理员操作**: 管理员代替用户操作时，记录管理员的ID
- **审计追踪**: 所有重要操作都会在 audit_logs 表中留下详细记录

---

## 16. 表关系图

```text
users (1) ──────────────────┬──── (N) messages
  │                         │
  │                         ├──── (N) user_states
  │                         │
  └── (1) user_extend       └──── (N) audit_logs
  │
  └── (N) user_history


emby_users (1) ──── (N) emby_user_history


group_configs (独立表，存储群组配置)


hitokoto (独立表，存储一言数据)
```

---

**版本**: 2.0
**更新**: 2025-12-04
