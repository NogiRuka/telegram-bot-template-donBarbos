# 🌸 樱色男孩 (Sakura Boy) 货币系统设计方案

> **状态**: 🚧 已搁置 (待未来开发)
> **日期**: 2025-12-09
> **背景**: 配合 Emby 机器人提升群组活跃度，主题为 BL/Gay/Lustful。

## 1. 核心概念

*   **货币名称**: **🌸 花瓣 (Petals)**
    *   *理由*: 契合“樱色”主题，意境唯美，有收集感。
*   **核心价值**: 
    *   用户通过活跃行为获取“花瓣”。
    *   “花瓣”可用于兑换 Emby 实际权益（时长/流量）或娱乐功能。

## 2. 功能模块设计

### A. 获取机制 (Earn)

1.  **每日签到 (Daily Check-in)**
    *   **命令**: `/sign` 或 `/checkin`
    *   **基础奖励**: 固定数值 (e.g., 10 花瓣)
    *   **随机暴击**: 概率获得 1.2x - 2.0x 倍率。
    *   **连续签到 (Streak)**:
        *   3天: +10%
        *   7天: +20%
        *   断签重置。
    *   **特色文案**: 
        *   签到成功后附带一句 **"Lustful Fortune"** (今日运势/骚话)。
        *   *Example*: "今日宜面基，忌独守空房。记得多喝水哦。"

2.  **新人礼包**: 首次绑定 Emby 账号赠送初始资金。
3.  **管理员发放**: `/grant @user <amount>` 用于活动发奖。

### B. 消耗机制 (Spend)

1.  **权益兑换 (Exchange)**
    *   兑换 Emby 账号有效期 (e.g., 100 花瓣 = 1天)。
    *   兑换 Emby 流量包 (如果有限制)。
2.  **抽奖/扭蛋 (Gacha)**
    *   小额消耗博取大额奖励。
3.  **特殊头衔**: 购买群组 Title (e.g., "樱花贵族")。

## 3. 数据库设计 (Schema)

建议新增两张表：

### 1. `user_wallets` (用户钱包表)
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `user_id` | BigInt (PK) | 关联 users.id |
| `balance` | Decimal/Int | 当前余额 |
| `total_earned` | Decimal/Int | 历史累计获取 |
| `streak_days` | Int | 当前连续签到天数 |
| `last_checkin_at` | DateTime | 上次签到时间 (用于判断断签) |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

### 2. `wallet_transactions` (流水记录表)
| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | BigInt (PK) | 自增主键 |
| `user_id` | BigInt | 关联 users.id |
| `amount` | Decimal/Int | 变动金额 (+/-) |
| `type` | String | 类型: `checkin`, `exchange`, `admin_grant`, `gacha` |
| `description` | String | 描述文本 (e.g., "2025-12-09 签到奖励") |
| `created_at` | DateTime | 发生时间 |

## 4. 交互示例

**用户签到**:
> **User**: /sign
> **Bot**: 🌸 **签到成功！**
>
> 📅 日期：2025-12-09
> 💰 获得：**25 花瓣** (基础 20 + 运气 5)
> 🔥 连签：第 3 天 (明日签到可获额外奖励)
> 👛 余额：105 花瓣
>
> 🔮 **今日运势**：宜主动出击，可能会遇到心软的神。

**查看钱包**:
> **User**: /wallet
> **Bot**: 🎒 **我的钱包**
>
> 👤 用户：Alviss
> 🌸 余额：**105 花瓣**
> 📊 排名：全群第 5 名
>
> [兑换中心] [流水明细]
