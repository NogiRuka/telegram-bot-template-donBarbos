# 🌸 桜色男孩 (Sakura Boy) - 樱露经济系统设计

> **状态**: 📝 设计中
> **日期**: 2025-12-24
> **适用**: Telegram Bot (Aiogram 3.x)
> **主题**: BL / Gay / Emby / 社交
> **官方网站**: https://lustfulboy.com

## 1. 核心概念 (Core Concepts)

为了契合“桜色男孩”的社区氛围，我们将摒弃传统的“金币/积分”概念，采用更具美感与现代感的设定。

*   **代币名称**: **樱露 (Sakura Dew)**
*   **代币符号**: `💧`（露水、清新、浓淡有致）
*   **核心逻辑**: 
    *   用户越活跃（签到、聊天、互动），收集到的“樱露”越多。
    *   “樱露”可用于兑换 Emby 观影特权或群组特殊身份。

## 2. 交互体验设计 (UX Design)

❌ **弃用**: 传统的 `/sign` 命令行交互  
✅ **采用**: 全 **UI/按钮** 驱动，无缝集成在主面板中

### A. 每日签到 (Daily Check-in)
*   **入口**: 在【主面板】显示 `[📅 每日签到]` 按钮。
*   **状态显示**: 
    *   未签到：按钮亮起，文案 `📅 每日签到`。
    *   已签到：按钮变灰，文案 `✅ 今日已签到`；面板显示 `💧 樱露余额: 120`。
*   **交互流程**:
    1.  用户点击 `[📅 每日签到]`。
    2.  Bot 弹窗 (Alert) 提示：
        > "签到成功！🌸
        > 获得: +20 樱露
        > 连续: 3 天（加成 +10%）
        >
        > 💬 今日运势: 宜面基，忌独守空房。"
    3.  Bot **静默刷新** 原消息，更新余额显示，不发送新消息刷屏。

### B. 欲望商店 (Desire Store)
*   **入口**: `[🛍️ 欲望商店]` 按钮。
*   **界面**: 使用内联键盘翻页展示可兑换商品。
*   **商品**:
    *   **Emby 时长**: 100 樱露 = 1天观看权。
    *   **补签卡**: 50 樱露 = 恢复断签。
    *   **特殊头衔**: "🌸 樱之主" / "🐶 忠犬" (群组 Title)。

## 3. 数据库设计 (Schema Optimization)

采用更语义化的命名，保持可扩展性与可读性。

### 1. `sakura_wallets`（用户钱包表）
用于存储用户的当前状态，每个用户一行。

| 字段名 | 类型 | 属性 | 说明 |
| :--- | :--- | :--- | :--- |
| `user_id` | BigInt | PK, FK | 关联 `users.id` |
| `balance` | Integer | Default 0 | 当前樱露余额 |
| `total_accumulated` | BigInt | Default 0 | 历史累计获取总量（用于等级/成就） |
| `streak_days` | Integer | Default 0 | 当前连续签到天数 |
| `last_checkin_date` | Date | Nullable | 上次签到日期 (用于计算断签) |
| `updated_at` | DateTime | Auto | 最后更新时间 |

### 2. `sakura_ledgers`（资产流水表）
不可变日志，用于审计和回溯。

| 字段名 | 类型 | 属性 | 说明 |
| :--- | :--- | :--- | :--- |
| `id` | BigInt | PK, Auto | 流水ID |
| `user_id` | BigInt | FK, Index | 关联 `users.id` |
| `amount` | Integer | Not Null | 变动数值 (正数为获取，负数为消耗) |
| `event_type` | Varchar(32)| Index | 事件类型: `daily_checkin`, `redeem_emby`, `admin_gift`, `refund` |
| `meta` | JSON | Nullable | 扩展信息（如: `{"streak": 5, "bonus": 1.2}`） |
| `created_at` | DateTime | Auto | 发生时间 |

## 4. 签到算法 (Algorithm)

*   **基础奖励**: 10 ~ 20 樱露（随机浮动，增加趣味性）
*   **连签加成**: 
    *   `bonus = base * min(streak * 0.1, 1.0)`
    *   上限为 100% 加成（连签 10 天达到双倍）
*   **断签逻辑**: 
    *   若 `today - last_checkin_date > 1`，则 `streak_days` 重置为 1

## 5. 开发计划 (Roadmap)

1.  **Phase 1**: 创建数据库表，实现 `SakuraEconomyService`（增删查改）。
2.  **Phase 2**: 修改主面板键盘，加入 `[📅 每日签到]` 按钮。
3.  **Phase 3**: 实现签到回调逻辑（`checkin_callback`）与弹窗反馈。
4.  **Phase 4**: 开发商店界面与兑换逻辑。
