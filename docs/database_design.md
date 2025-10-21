# 数据库设计文档

## 概述

本文档详细描述了 Telegram Bot 项目的数据库设计，包含所有表结构、字段定义、索引配置和约束关系。

**数据库类型**: MySQL 8.0+  
**字符集**: utf8mb4  
**排序规则**: utf8mb4_unicode_ci  

---

## 1. 用户表 (users)

### 表描述
存储 Telegram 用户的基本信息和状态数据。

### 字段定义

| 字段名 | 类型 | 长度 | 是否为空 | 默认值 | 索引 | 注释 |
|--------|------|------|----------|--------|------|------|
| id | BIGINT | - | NO | - | PRIMARY | 用户ID，Telegram唯一标识 |
| first_name | VARCHAR | 255 | NO | - | - | 用户名字 |
| last_name | VARCHAR | 255 | YES | NULL | - | 用户姓氏 |
| username | VARCHAR | 255 | YES | NULL | INDEX | 用户名，不含@符号 |
| phone_number | VARCHAR | 20 | YES | NULL | - | 电话号码，国际格式 |
| bio | TEXT | - | YES | NULL | - | 个人简介 |
| language_code | VARCHAR | 10 | YES | NULL | - | 语言代码，ISO 639-1 |
| referrer | VARCHAR | 255 | YES | NULL | - | 推荐人信息 |
| referrer_id | BIGINT | - | YES | NULL | INDEX | 推荐人用户ID |
| last_activity_at | DATETIME | - | YES | NULL | INDEX | 最后活动时间 |
| is_admin | TINYINT | 1 | NO | 0 | INDEX | 是否管理员 |
| is_suspicious | TINYINT | 1 | NO | 0 | INDEX | 是否可疑用户 |
| is_block | TINYINT | 1 | NO | 0 | INDEX | 是否被封禁 |
| is_premium | TINYINT | 1 | NO | 0 | INDEX | 是否高级用户 |
| is_bot | TINYINT | 1 | NO | 0 | - | 是否机器人 |
| message_count | INT | - | NO | 0 | - | 消息计数 |
| created_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 创建时间 |
| updated_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 更新时间 |
| is_deleted | TINYINT | 1 | NO | 0 | INDEX | 是否已删除 |
| deleted_at | DATETIME | - | YES | NULL | INDEX | 删除时间 |
| operated_by | BIGINT | - | YES | NULL | - | 操作者ID |

### 索引配置

```sql
-- 主键索引
PRIMARY KEY (id)

-- 单列索引
INDEX ix_users_username (username)
INDEX ix_users_referrer_id (referrer_id)
INDEX ix_users_last_activity_at (last_activity_at)
INDEX ix_users_is_admin (is_admin)
INDEX ix_users_is_suspicious (is_suspicious)
INDEX ix_users_is_block (is_block)
INDEX ix_users_is_premium (is_premium)
INDEX ix_users_is_deleted (is_deleted)

-- 复合索引
INDEX idx_users_created_at (created_at)
INDEX idx_users_updated_at (updated_at)
INDEX idx_users_last_activity (last_activity_at)
INDEX idx_users_referrer_id (referrer_id)
INDEX idx_users_status (is_block, is_suspicious)
INDEX idx_users_admin_premium (is_admin, is_premium)
INDEX idx_users_deleted (is_deleted)
INDEX idx_users_deleted_at (deleted_at)
```

### 创建语句

```sql
CREATE TABLE users (
    id BIGINT NOT NULL COMMENT '用户ID，Telegram唯一标识',
    first_name VARCHAR(255) NOT NULL COMMENT '用户名字',
    last_name VARCHAR(255) COMMENT '用户姓氏',
    username VARCHAR(255) COMMENT '用户名，不含@符号',
    phone_number VARCHAR(20) COMMENT '电话号码，国际格式',
    bio TEXT COMMENT '个人简介',
    language_code VARCHAR(10) COMMENT '语言代码，ISO 639-1',
    referrer VARCHAR(255) COMMENT '推荐人信息',
    referrer_id BIGINT COMMENT '推荐人用户ID',
    last_activity_at DATETIME COMMENT '最后活动时间',
    is_admin TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否管理员',
    is_suspicious TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否可疑用户',
    is_block TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否被封禁',
    is_premium TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否高级用户',
    is_bot TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否机器人',
    message_count INT NOT NULL DEFAULT 0 COMMENT '消息计数',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已删除',
    deleted_at DATETIME COMMENT '删除时间',
    operated_by BIGINT COMMENT '操作者ID',
    PRIMARY KEY (id),
    INDEX ix_users_username (username),
    INDEX ix_users_referrer_id (referrer_id),
    INDEX ix_users_last_activity_at (last_activity_at),
    INDEX ix_users_is_admin (is_admin),
    INDEX ix_users_is_suspicious (is_suspicious),
    INDEX ix_users_is_block (is_block),
    INDEX ix_users_is_premium (is_premium),
    INDEX ix_users_is_deleted (is_deleted),
    INDEX idx_users_created_at (created_at),
    INDEX idx_users_updated_at (updated_at),
    INDEX idx_users_status (is_block, is_suspicious),
    INDEX idx_users_admin_premium (is_admin, is_premium),
    INDEX idx_users_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 2. 消息记录表 (messages)

### 表描述
存储用户发送给机器人的消息记录，用于统计和分析。

### 字段定义

| 字段名 | 类型 | 长度 | 是否为空 | 默认值 | 索引 | 注释 |
|--------|------|------|----------|--------|------|------|
| id | INT | - | NO | AUTO_INCREMENT | PRIMARY | 消息记录ID，自增主键 |
| message_id | BIGINT | - | NO | - | INDEX | Telegram消息ID |
| user_id | BIGINT | - | NO | - | INDEX | 发送者用户ID |
| chat_id | BIGINT | - | NO | - | INDEX | 聊天ID |
| message_type | ENUM | - | NO | 'text' | INDEX | 消息类型 |
| content | TEXT | - | YES | NULL | - | 消息内容摘要 |
| file_id | VARCHAR | 255 | YES | NULL | - | 文件ID |
| file_size | INT | - | YES | NULL | - | 文件大小 |
| reply_to_message_id | BIGINT | - | YES | NULL | INDEX | 回复的消息ID |
| forward_from_user_id | BIGINT | - | YES | NULL | INDEX | 转发来源用户ID |
| forward_from_chat_id | BIGINT | - | YES | NULL | INDEX | 转发来源聊天ID |
| created_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 创建时间 |
| updated_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 更新时间 |

### 枚举值定义

```sql
-- message_type 枚举值
ENUM('text', 'photo', 'video', 'audio', 'voice', 'document', 'sticker', 
     'animation', 'location', 'contact', 'poll', 'dice', 'game', 
     'invoice', 'successful_payment', 'video_note', 'venue', 
     'web_app_data', 'passport_data', 'proximity_alert', 
     'forum_topic_created', 'forum_topic_edited', 'forum_topic_closed', 
     'forum_topic_reopened', 'general_forum_topic_hidden', 
     'general_forum_topic_unhidden', 'video_chat_scheduled', 
     'video_chat_started', 'video_chat_ended', 
     'video_chat_participants_invited', 'other')
```

### 创建语句

```sql
CREATE TABLE messages (
    id INT NOT NULL AUTO_INCREMENT COMMENT '消息记录ID，自增主键',
    message_id BIGINT NOT NULL COMMENT 'Telegram消息ID',
    user_id BIGINT NOT NULL COMMENT '发送者用户ID',
    chat_id BIGINT NOT NULL COMMENT '聊天ID',
    message_type ENUM('text', 'photo', 'video', 'audio', 'voice', 'document', 'sticker', 'animation', 'location', 'contact', 'poll', 'dice', 'game', 'invoice', 'successful_payment', 'video_note', 'venue', 'web_app_data', 'passport_data', 'proximity_alert', 'forum_topic_created', 'forum_topic_edited', 'forum_topic_closed', 'forum_topic_reopened', 'general_forum_topic_hidden', 'general_forum_topic_unhidden', 'video_chat_scheduled', 'video_chat_started', 'video_chat_ended', 'video_chat_participants_invited', 'other') NOT NULL DEFAULT 'text' COMMENT '消息类型',
    content TEXT COMMENT '消息内容摘要',
    file_id VARCHAR(255) COMMENT '文件ID',
    file_size INT COMMENT '文件大小',
    reply_to_message_id BIGINT COMMENT '回复的消息ID',
    forward_from_user_id BIGINT COMMENT '转发来源用户ID',
    forward_from_chat_id BIGINT COMMENT '转发来源聊天ID',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX ix_messages_message_id (message_id),
    INDEX ix_messages_user_id (user_id),
    INDEX ix_messages_chat_id (chat_id),
    INDEX ix_messages_message_type (message_type),
    INDEX ix_messages_reply_to_message_id (reply_to_message_id),
    INDEX ix_messages_forward_from_user_id (forward_from_user_id),
    INDEX ix_messages_forward_from_chat_id (forward_from_chat_id),
    INDEX ix_messages_created_at (created_at),
    INDEX ix_messages_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 3. 用户状态表 (user_states)

### 表描述
存储用户在机器人对话中的状态信息，用于多步骤交互。

### 字段定义

| 字段名 | 类型 | 长度 | 是否为空 | 默认值 | 索引 | 注释 |
|--------|------|------|----------|--------|------|------|
| user_id | BIGINT | - | NO | - | PRIMARY | 用户ID |
| state | VARCHAR | 255 | YES | NULL | INDEX | 当前状态 |
| data | JSON | - | YES | NULL | - | 状态数据 |
| created_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 创建时间 |
| updated_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 更新时间 |

### 创建语句

```sql
CREATE TABLE user_states (
    user_id BIGINT NOT NULL COMMENT '用户ID',
    state VARCHAR(255) COMMENT '当前状态',
    data JSON COMMENT '状态数据',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (user_id),
    INDEX ix_user_states_state (state),
    INDEX ix_user_states_created_at (created_at),
    INDEX ix_user_states_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 4. 系统配置表 (configs)

### 表描述
存储系统的动态配置参数，支持多种数据类型。

### 字段定义

| 字段名 | 类型 | 长度 | 是否为空 | 默认值 | 索引 | 注释 |
|--------|------|------|----------|--------|------|------|
| key | VARCHAR | 255 | NO | - | PRIMARY | 配置键名 |
| value | TEXT | - | YES | NULL | - | 配置值 |
| config_type | ENUM | - | NO | 'string' | INDEX | 配置类型 |
| default_value | TEXT | - | YES | NULL | - | 默认值 |
| description | TEXT | - | YES | NULL | - | 配置描述 |
| category | VARCHAR | 100 | YES | NULL | INDEX | 配置分类 |
| is_public | TINYINT | 1 | NO | 0 | INDEX | 是否公开 |
| is_editable | TINYINT | 1 | NO | 1 | INDEX | 是否可编辑 |
| created_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 创建时间 |
| updated_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 更新时间 |
| is_deleted | TINYINT | 1 | NO | 0 | INDEX | 是否已删除 |
| deleted_at | DATETIME | - | YES | NULL | INDEX | 删除时间 |
| operated_by | BIGINT | - | YES | NULL | - | 操作者ID |

### 枚举值定义

```sql
-- config_type 枚举值
ENUM('string', 'integer', 'float', 'boolean', 'json', 'text', 'list', 'dict')
```

### 创建语句

```sql
CREATE TABLE configs (
    `key` VARCHAR(255) NOT NULL COMMENT '配置键名',
    value TEXT COMMENT '配置值',
    config_type ENUM('string', 'integer', 'float', 'boolean', 'json', 'text', 'list', 'dict') NOT NULL DEFAULT 'string' COMMENT '配置类型',
    default_value TEXT COMMENT '默认值',
    description TEXT COMMENT '配置描述',
    category VARCHAR(100) COMMENT '配置分类',
    is_public TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否公开',
    is_editable TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否可编辑',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否已删除',
    deleted_at DATETIME COMMENT '删除时间',
    operated_by BIGINT COMMENT '操作者ID',
    PRIMARY KEY (`key`),
    INDEX ix_configs_config_type (config_type),
    INDEX ix_configs_category (category),
    INDEX ix_configs_is_public (is_public),
    INDEX ix_configs_is_editable (is_editable),
    INDEX ix_configs_created_at (created_at),
    INDEX ix_configs_updated_at (updated_at),
    INDEX ix_configs_is_deleted (is_deleted),
    INDEX ix_configs_deleted_at (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 5. 审计日志表 (audit_logs)

### 表描述
记录系统中所有重要操作的审计日志，用于安全审计和行为分析。

### 字段定义

| 字段名 | 类型 | 长度 | 是否为空 | 默认值 | 索引 | 注释 |
|--------|------|------|----------|--------|------|------|
| id | INT | - | NO | AUTO_INCREMENT | PRIMARY | 日志ID，自增主键 |
| action_type | ENUM | - | NO | - | INDEX | 操作类型 |
| user_id | BIGINT | - | YES | NULL | INDEX | 操作用户ID |
| target_type | VARCHAR | 100 | YES | NULL | INDEX | 目标对象类型 |
| target_id | VARCHAR | 255 | YES | NULL | INDEX | 目标对象ID |
| description | TEXT | - | YES | NULL | - | 操作描述 |
| details | JSON | - | YES | NULL | - | 详细信息 |
| ip_address | VARCHAR | 45 | YES | NULL | INDEX | IP地址 |
| user_agent | TEXT | - | YES | NULL | - | 用户代理 |
| session_id | VARCHAR | 255 | YES | NULL | INDEX | 会话ID |
| operator_name | VARCHAR | 255 | YES | NULL | INDEX | 操作者名称 |
| is_success | TINYINT | 1 | NO | 1 | INDEX | 操作是否成功 |
| error_message | TEXT | - | YES | NULL | - | 错误信息 |
| duration_ms | INT | - | YES | NULL | INDEX | 操作耗时(毫秒) |
| created_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 创建时间 |
| updated_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 更新时间 |

### 枚举值定义

```sql
-- action_type 枚举值
ENUM('user_create', 'user_update', 'user_delete', 'user_block', 'user_unblock', 
     'user_promote', 'user_demote', 'user_login', 'user_logout',
     'message_send', 'message_delete', 'message_edit', 'message_forward', 'message_reply',
     'config_create', 'config_update', 'config_delete', 'config_reset',
     'system_start', 'system_stop', 'system_restart', 'system_backup', 'system_restore',
     'admin_login', 'admin_logout', 'admin_action', 'admin_query', 'admin_export',
     'security_login_fail', 'security_suspicious', 'security_rate_limit', 'security_permission_deny',
     'other')
```

### 创建语句

```sql
CREATE TABLE audit_logs (
    id INT NOT NULL AUTO_INCREMENT COMMENT '日志ID，自增主键',
    action_type ENUM('user_create', 'user_update', 'user_delete', 'user_block', 'user_unblock', 'user_promote', 'user_demote', 'user_login', 'user_logout', 'message_send', 'message_delete', 'message_edit', 'message_forward', 'message_reply', 'config_create', 'config_update', 'config_delete', 'config_reset', 'system_start', 'system_stop', 'system_restart', 'system_backup', 'system_restore', 'admin_login', 'admin_logout', 'admin_action', 'admin_query', 'admin_export', 'security_login_fail', 'security_suspicious', 'security_rate_limit', 'security_permission_deny', 'other') NOT NULL COMMENT '操作类型',
    user_id BIGINT COMMENT '操作用户ID',
    target_type VARCHAR(100) COMMENT '目标对象类型',
    target_id VARCHAR(255) COMMENT '目标对象ID',
    description TEXT COMMENT '操作描述',
    details JSON COMMENT '详细信息',
    ip_address VARCHAR(45) COMMENT 'IP地址',
    user_agent TEXT COMMENT '用户代理',
    session_id VARCHAR(255) COMMENT '会话ID',
    operator_name VARCHAR(255) COMMENT '操作者名称',
    is_success TINYINT(1) NOT NULL DEFAULT 1 COMMENT '操作是否成功',
    error_message TEXT COMMENT '错误信息',
    duration_ms INT COMMENT '操作耗时(毫秒)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX ix_audit_logs_action_type (action_type),
    INDEX ix_audit_logs_user_id (user_id),
    INDEX ix_audit_logs_target_type (target_type),
    INDEX ix_audit_logs_target_id (target_id),
    INDEX ix_audit_logs_ip_address (ip_address),
    INDEX ix_audit_logs_session_id (session_id),
    INDEX ix_audit_logs_operator_name (operator_name),
    INDEX ix_audit_logs_is_success (is_success),
    INDEX ix_audit_logs_duration_ms (duration_ms),
    INDEX ix_audit_logs_created_at (created_at),
    INDEX ix_audit_logs_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 6. 统计数据表 (statistics)

### 表描述
存储系统的各种统计数据，用于数据分析和报表生成。

### 字段定义

| 字段名 | 类型 | 长度 | 是否为空 | 默认值 | 索引 | 注释 |
|--------|------|------|----------|--------|------|------|
| id | INT | - | NO | AUTO_INCREMENT | PRIMARY | 统计ID，自增主键 |
| statistic_type | ENUM | - | NO | - | INDEX | 统计类型 |
| key | VARCHAR | 255 | NO | - | INDEX | 统计键名 |
| value | BIGINT | - | NO | 0 | INDEX | 统计值 |
| date | DATE | - | NO | - | INDEX | 统计日期 |
| hour | TINYINT | - | YES | NULL | INDEX | 统计小时(0-23) |
| metadata | JSON | - | YES | NULL | - | 元数据 |
| created_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 创建时间 |
| updated_at | DATETIME | - | NO | CURRENT_TIMESTAMP | INDEX | 更新时间 |

### 枚举值定义

```sql
-- statistic_type 枚举值
ENUM('daily', 'hourly', 'monthly', 'yearly', 'total', 'custom')
```

### 创建语句

```sql
CREATE TABLE statistics (
    id INT NOT NULL AUTO_INCREMENT COMMENT '统计ID，自增主键',
    statistic_type ENUM('daily', 'hourly', 'monthly', 'yearly', 'total', 'custom') NOT NULL COMMENT '统计类型',
    `key` VARCHAR(255) NOT NULL COMMENT '统计键名',
    value BIGINT NOT NULL DEFAULT 0 COMMENT '统计值',
    date DATE NOT NULL COMMENT '统计日期',
    hour TINYINT COMMENT '统计小时(0-23)',
    metadata JSON COMMENT '元数据',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX ix_statistics_statistic_type (statistic_type),
    INDEX ix_statistics_key (`key`),
    INDEX ix_statistics_value (value),
    INDEX ix_statistics_date (date),
    INDEX ix_statistics_hour (hour),
    INDEX ix_statistics_created_at (created_at),
    INDEX ix_statistics_updated_at (updated_at),
    UNIQUE INDEX idx_statistics_unique (statistic_type, `key`, date, hour)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 7. 外键约束

### 用户推荐关系
```sql
-- 用户表的推荐人关系（自引用）
ALTER TABLE users ADD CONSTRAINT fk_users_referrer_id 
FOREIGN KEY (referrer_id) REFERENCES users(id) ON DELETE SET NULL;
```

### 消息关联关系
```sql
-- 消息表与用户表的关联
ALTER TABLE messages ADD CONSTRAINT fk_messages_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- 消息回复关系（自引用）
ALTER TABLE messages ADD CONSTRAINT fk_messages_reply_to_message_id 
FOREIGN KEY (reply_to_message_id) REFERENCES messages(message_id) ON DELETE SET NULL;

-- 消息转发关系
ALTER TABLE messages ADD CONSTRAINT fk_messages_forward_from_user_id 
FOREIGN KEY (forward_from_user_id) REFERENCES users(id) ON DELETE SET NULL;
```

### 用户状态关联
```sql
-- 用户状态表与用户表的关联
ALTER TABLE user_states ADD CONSTRAINT fk_user_states_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
```

### 审计日志关联
```sql
-- 审计日志与用户表的关联
ALTER TABLE audit_logs ADD CONSTRAINT fk_audit_logs_user_id 
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
```

---

## 8. 数据库初始化脚本

### 创建数据库
```sql
CREATE DATABASE telegram_bot 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE telegram_bot;
```

### 设置时区
```sql
SET time_zone = '+00:00';
```

### 创建所有表
按照上述各表的创建语句依次执行。

### 添加外键约束
按照外键约束部分的语句依次执行。

---

## 9. 性能优化建议

### 索引优化
1. 定期分析查询性能，根据实际使用情况调整索引
2. 避免过多的复合索引，影响写入性能
3. 对于大表，考虑分区策略

### 数据清理
1. 定期清理过期的审计日志和统计数据
2. 软删除的数据定期物理删除
3. 消息表数据按时间分区存储

### 查询优化
1. 避免全表扫描，合理使用索引
2. 大数据量查询使用分页
3. 统计查询使用专门的统计表

---

## 10. 备份策略

### 定期备份
- 每日全量备份
- 每小时增量备份
- 重要操作前手动备份

### 备份验证
- 定期恢复测试
- 备份文件完整性检查
- 跨地域备份存储

---

**文档版本**: 1.0  
**最后更新**: 2025-10-21  
**维护者**: Telegram Bot Template Team