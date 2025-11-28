# 数据库设计文档

## 概述

**数据库**: MySQL 8.0+  
**字符集**: utf8mb4  
**排序规则**: utf8mb4_unicode_ci  

---

## 1. 用户表 (users)

存储 Telegram 用户信息和状态。

| 字段名 | 类型 | 长度 | 空值 | 默认值 | 索引 | 注释 |
|--------|------|------|------|--------|------|------|
| id | BIGINT | - | NO | - | PK | 用户ID |
| first_name | VARCHAR | 255 | NO | - | - | 名字 |
| last_name | VARCHAR | 255 | YES | NULL | - | 姓氏 |
| username | VARCHAR | 255 | YES | NULL | IDX | 用户名 |
| phone_number | VARCHAR | 20 | YES | NULL | - | 电话 |
| bio | TEXT | - | YES | NULL | - | 简介 |
| language_code | VARCHAR | 10 | YES | NULL | - | 语言 |
| last_activity_at | DATETIME | - | YES | NULL | IDX | 最后活动 |
| is_admin | TINYINT | 1 | NO | 0 | IDX | 管理员 |
| is_suspicious | TINYINT | 1 | NO | 0 | IDX | 可疑用户 |
| is_block | TINYINT | 1 | NO | 0 | IDX | 封禁 |
| is_premium | TINYINT | 1 | NO | 0 | IDX | 高级用户 |
| is_bot | TINYINT | 1 | NO | 0 | - | 机器人 |
| message_count | INT | - | NO | 0 | - | 消息数 |
| created_at | DATETIME | - | NO | NOW() | IDX | 创建时间 |
| created_by | BIGINT | - | YES | NULL | IDX | 创建者ID |
| updated_at | DATETIME | - | NO | NOW() | IDX | 更新时间 |
| updated_by | BIGINT | - | YES | NULL | IDX | 更新者ID |
| is_deleted | TINYINT | 1 | NO | 0 | IDX | 已删除 |
| deleted_at | DATETIME | - | YES | NULL | IDX | 删除时间 |
| deleted_by | BIGINT | - | YES | NULL | IDX | 删除者ID |

```sql
CREATE TABLE users (
    id BIGINT NOT NULL COMMENT '用户ID',
    first_name VARCHAR(255) NOT NULL COMMENT '名字',
    last_name VARCHAR(255) COMMENT '姓氏',
    username VARCHAR(255) COMMENT '用户名',
    phone_number VARCHAR(20) COMMENT '电话',
    bio TEXT COMMENT '简介',
    language_code VARCHAR(10) COMMENT '语言',

    last_activity_at DATETIME COMMENT '最后活动',
    is_admin TINYINT(1) NOT NULL DEFAULT 0 COMMENT '管理员',
    is_suspicious TINYINT(1) NOT NULL DEFAULT 0 COMMENT '可疑用户',
    is_block TINYINT(1) NOT NULL DEFAULT 0 COMMENT '封禁',
    is_premium TINYINT(1) NOT NULL DEFAULT 0 COMMENT '高级用户',
    is_bot TINYINT(1) NOT NULL DEFAULT 0 COMMENT '机器人',
    message_count INT NOT NULL DEFAULT 0 COMMENT '消息数',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    created_by BIGINT COMMENT '创建者ID',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    updated_by BIGINT COMMENT '更新者ID',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '已删除',
    deleted_at DATETIME COMMENT '删除时间',
    deleted_by BIGINT COMMENT '删除者ID',
    PRIMARY KEY (id),
    INDEX ix_users_username (username),
    INDEX ix_users_last_activity_at (last_activity_at),
    INDEX ix_users_is_admin (is_admin),
    INDEX ix_users_is_suspicious (is_suspicious),
    INDEX ix_users_is_block (is_block),
    INDEX ix_users_is_premium (is_premium),
    INDEX ix_users_is_deleted (is_deleted),
    INDEX ix_users_created_at (created_at),
    INDEX ix_users_created_by (created_by),
    INDEX ix_users_updated_at (updated_at),
    INDEX ix_users_updated_by (updated_by),
    INDEX ix_users_deleted_at (deleted_at),
    INDEX ix_users_deleted_by (deleted_by)
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

## 7. 外键约束

```sql
-- 消息关联
ALTER TABLE messages ADD CONSTRAINT fk_messages_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 用户状态关联
ALTER TABLE user_states ADD CONSTRAINT fk_user_states_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 审计日志关联
ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
```

---

## 8. 初始化脚本

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

## 9. 字段含义说明

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

**版本**: 1.1  
**更新**: 2025-10-21