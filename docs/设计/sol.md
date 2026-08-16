我目前有一个关于bl影视和gv的emby服务器 ，有电报群组以及机器人，下面是机器人的结构，目前群组不太活跃，是通过机器人指定时间开放注册emby账号，怎么做可以让这个emby活跃扩大起来

# 项目结构总览

本项目是基于 **Aiogram 3** 的 Telegram Bot，采用分层架构：

- `handlers/`：处理 Telegram 更新（命令、按钮、消息）
- `services/`：业务逻辑
- `database/`：数据库模型与迁移
- `utils/`：通用工具
- `api/`：HTTP / 管理 API
- `config` & `core`：配置与全局对象

---

## 根目录

```text
telegram-bot-template-donBarbos/
├─ bot/                # 机器人主代码
├─ docs/               # 设计与说明文档
├─ assets/             # 图片、banner 等静态资源
├─ .trae/              # Trae 规则与说明
├─ .github/            # GitHub Actions 工作流
├─ Dockerfile          # Docker 构建配置
├─ docker-compose.yml  # Docker 编排
├─ README.md           # 项目说明
└─ alembic.ini         # Alembic 迁移配置
```

---

## bot 目录结构

```text
bot/
├─ __main__.py         # Bot 启动入口（python -m bot）
├─ analytics/          # 分析上报及 Google Analytics 客户端
├─ api/                # FastAPI 内置 API
│  ├─ app.py           # API 应用与生命周期配置
│  ├─ routes/          # 管理员、用户、认证、Webhook 等路由
│  └─ __main__.py      # API 启动入口
├─ assets/             # Bot 使用的图片、字体等资源
├─ cache/              # 缓存与序列化实现
├─ config/             # 配置模块：键名、默认值、功能映射与依赖关系
│  ├─ constants.py     # 配置键常量，统一定义配置表中的 key
│  ├─ features.py      # 功能依赖关系，例如 register 依赖 account
│  ├─ mappings.py      # 默认配置、功能开关映射、面板可见功能定义
│  └─ __init__.py      # 导出常量与映射，供外部统一导入
├─ core/               # 全局 settings、loader、Emby 及核心常量
├─ database/           # 数据库连接、ORM 模型、种子数据与 Alembic 迁移
│  ├─ models/          # SQLAlchemy ORM 模型
│  └─ migrations/      # Alembic 迁移版本
├─ filters/            # Aiogram Filter 扩展
├─ handlers/           # Telegram 交互层
│  ├─ admin/            # 管理员面板与管理操作
│  ├─ command/          # 用户、管理员、Owner 命令
│  ├─ group/            # 群组消息与群组配置
│  ├─ owner/            # Owner 专属功能
│  └─ user/             # 用户功能与业务交互
├─ keyboards/          # Inline/Reply 键盘与默认命令
├─ middlewares/        # Aiogram 中间件
├─ runtime/            # 启动与关闭钩子
├─ services/           # 业务服务层
│  ├─ emby_metadata/   # Emby 元数据匹配与来源处理
│  │  ├─ matching.py   # 元数据匹配逻辑
│  │  ├─ models.py     # 元数据相关数据模型
│  │  └─ sources/      # 外部元数据来源适配器
│  └─ ...              # 配置、用户、问答、货币等业务服务
├─ states/             # FSM 状态定义
├─ tests/              # 测试与调试工具
├─ tools/              # 开发辅助脚本
└─ utils/              # 通用工具函数










你现在的问题本质上不是“Emby 功能不够”，而是整个社区只有一个主要行为：

> 等机器人开放注册 → 注册 Emby → 看片 → 潜水。

这个路径天然不会产生群聊活跃度。要扩大，应该把机器人从“账号注册工具”改成“社区运营中枢”，建立「拉新 → 激活 → 使用 → 互动 → 留存 → 邀请」的循环。

考虑到你的内容包含 BL 影视以及 GV/成人向内容，建议明确限制为成年人社区，并设置 18+ 声明、违规资源举报、版权投诉处理机制；不要把未成年人相关内容、偷拍/非自愿内容等纳入社区。

我会优先这样改。

第一层，是把“定时开放注册”升级成“注册事件”。

你现在大概率是：

```text
管理员设定时间
   ↓
机器人开放注册
   ↓
用户注册
   ↓
结束
```

建议变成：

```text
注册预告
 ↓
预约提醒
 ↓
倒计时
 ↓
限量开放
 ↓
注册成功
 ↓
新手任务
 ↓
进入 Emby
 ↓
机器人推荐内容
 ↓
群内互动
```

比如注册前 24 小时：

> 🎬 本周 Emby 开放注册
> 周六 21:00 开放
> 本轮 30 个名额
> 当前预约：126 人
>
> [预约注册] [邀请好友] [看看本周更新]

开放前 30 分钟机器人再主动提醒预约的人。

这样你的注册活动本身就是群里的一个周期性事件。

从代码结构上可以增加：

```text
services/
├─ registration_campaign/
│  ├─ service.py
│  ├─ scheduler.py
│  └─ models.py

handlers/user/
├─ registration_campaign.py

database/models/
├─ registration_campaign.py
├─ registration_reservation.py
```

数据库可以记录：

```text
campaign
- id
- start_time
- end_time
- quota
- registered_count

reservation
- telegram_id
- campaign_id
- invited_by
- status
```

第二层，是解决“注册以后人就消失”。

这是你目前最需要改的地方。

注册成功之后，不应该只返回：

> 注册成功，用户名 xxx。

而应该自动进入一个 onboarding 流程：

```text
注册成功
 ↓
选择兴趣
 ↓
生成个人推荐
 ↓
收藏
 ↓
开始观看
```

例如：

> ✅ Emby 创建成功
>
> 为了给你推荐内容，选一下你比较喜欢的：
>
> [🇯🇵 日腐]
> [🇹🇭 泰腐]
> [🇰🇷 韩腐]
> [🇨🇳 华语]
> [🌍 欧美]
> [🔞 GV]
> [🎬 剧集]
> [🎞️ 电影]

之后机器人保存用户兴趣标签。

你的数据库 User 可以增加类似：

```text
user_preferences

telegram_id
genres
countries
actors
adult_enabled
notification_enabled
```

以后机器人就不再只是 `/register`，而是可以做：

```text
/推荐
/本周更新
/猜你喜欢
/最近热门
/演员
/搜索
/收藏
/继续观看
```

第三层，机器人必须知道 Emby 里面发生了什么。

这是我认为你这个项目最值得做的技术升级。

你已经有：

```text
services/emby_metadata/
```

可以继续增加：

```text
services/emby_activity/
├─ client.py
├─ statistics.py
├─ ranking.py
└─ notification.py
```

周期性读取 Emby：

```text
新增影片
新增剧集
最近观看
播放次数
活跃用户
热门影片
```

然后机器人自动生成内容。

例如每天晚上：

> 🔥 今日 Emby 热播
>
> 1. xxx — 37 人观看
> 2. xxx — 29 人观看
> 3. xxx — 24 人观看
>
> 🆕 今日新增 17 部
>
> [查看榜单] [随机看片]

这样即使管理员不讲话，机器人也可以每天制造话题。

但不要刷屏。

推荐：

```text
每日：1 条
每周：1 条周报
新增大量资源：1 条
注册活动：1-3 条
```

第四层，建立“资源更新 → 群讨论”的闭环。

例如新增一部作品：

> 🆕 新片入库
>
> 《XXX》
>
> 🇯🇵 日本
> ⭐ 评分 8.2
> 🎭 主演 xxx
>
> 已加入 Emby。
>
> 看过了吗？
>
> 👍 好看  |  😐 一般  |  ❤️ 神作
>
> [打开 Emby] [查看更多]

点击后记录 Telegram 投票。

于是你可以做：

```text
/group rating
```

而不是只依赖 Telegram 的闲聊。

甚至可以显示：

> Emby 站内 126 人看过
> 群友评分 8.7
> 37 人收藏

这种“社区数据”非常容易形成归属感。

第五层，做每周榜单。

这个对影视社区特别有效。

比如固定周日：

> 🏆 本周 Emby TOP 10
>
> ① xxx
> 👀 178 次播放
>
> ② xxx
> 👀 142 次播放
>
> ③ xxx
> 👀 119 次播放
>
> 本周黑马：XXX
>
> [完整榜单]

甚至分别做：

```text
BL TOP10
GV TOP10
电影 TOP10
剧集 TOP10
新人最爱
冷门佳作
```

这比单纯发“今天更新了 20 部”有互动价值。

第六层，加“求片系统”。

这个非常适合你现有 Aiogram 架构。

增加：

```text
handlers/user/request_media.py
services/media_request/
database/models/media_request.py
```

用户：

```text
/求片
```

机器人：

> 请输入片名 / 演员 / TMDB / IMDb。

提交之后生成：

> 🙋 求片 #1821
>
> 《XXX》
>
> 👤 DR.Lu 请求
>
> 👍 23 人也想看
>
> [我也想看]

管理员后台看到：

```text
🔥 67 votes  XXX
🔥 42 votes  XXX
🔥 31 votes  XXX
```

管理员添加后机器人自动通知：

> ✅ 你之前求的《XXX》已经入库。

这会形成非常强的回访机制：

```text
用户需求
 ↓
社区投票
 ↓
管理员补资源
 ↓
机器人通知
 ↓
用户回来观看
```

第七层，可以加入“愿望单”。

例如：

```text
❤️ 收藏
🔔 上线提醒
```

用户搜索一个还不存在的影片：

> 暂未收录《XXX》
>
> [加入愿望单]

等以后入库：

> 🔔 你关注的《XXX》已经加入 Emby。

这种通知的点击率通常会比普通群公告高很多，因为是针对个人兴趣的。

第八层，邀请机制不要直接做成无脑拉人。

不要设计：

> 拉 5 个人送永久免费。

这样很容易把群搞成垃圾流量。

更合适的是：

```text
邀请 1 个有效用户
→ 增加下一次注册优先权

邀请 3 个活跃用户
→ 获得邀请码

邀请 5 个活跃用户
→ 获得特殊身份组
```

“有效用户”可以定义为：

```text
注册 Emby
+
加入群
+
7 天内观看 ≥ X 分钟
```

而不是单纯 `/start`。

数据库：

```text
referrals

inviter_id
invitee_id
created_at
registered
activated
qualified
```

机器人里可以：

```text
/邀请
```

返回：

> 你的专属邀请：
>
> t.me/xxxbot?start=ref_18271
>
> 已邀请：7
> 有效用户：4
> 本月排名：18
>
> 再邀请 1 名有效用户可获得下一轮优先注册资格。

第九层，我建议你加入“等级体系”，但是不要搞得太复杂。

例如：

```text
Lv.0 游客
Lv.1 观众
Lv.2 影迷
Lv.3 资深影迷
Lv.4 馆藏会员
```

经验来源可以是：

```text
每日签到          +1
观看内容          +X
参与评分          +2
求片被采纳        +5
帮助其他群友      +3
邀请有效成员      +10
```

不要让“群里疯狂发消息”成为主要经验来源，否则最后会变成水群。

正确的激励应该围绕：

```text
看
评
藏
求
荐
邀
```

第十层，可以做一个非常简单但很有效的 `/随机看片`。

例如：

> 🎲 今天不知道看什么？
>
> 《XXX》
>
> 2025 · 日本 · BL
>
> ⭐ 8.1
>
> Emby 内 63 人看过
>
> [换一个]
> [加入收藏]
> [打开 Emby]

甚至：

```text
🎲 随机 BL
🎲 随机 GV
🎲 随机电影
🎲 随机剧集
🎲 高分冷门
```

这个功能的开发成本低，但使用频率可能很高。

第十一层，是“看片房 / 同步看片活动”。

不一定需要真的同步播放。

例如周五机器人：

> 🍿 周五看片夜
>
> 本周群看片：
> 《XXX》
>
> 🕘 22:00
>
> 已报名：37 人
>
> [我要参加]

晚上：

> 🍿 开始看片
>
> Emby → 搜索《XXX》
>
> 群里可以边看边聊。

结束后：

> 这部你打几分？
>
> 1 2 3 4 5

这才是真正能够把 Emby 用户转化成 Telegram 活跃用户的活动。

第十二层，是做“个人周报”。

比如机器人私聊：

> 📊 你的本周看片报告
>
> 🎬 看了 7 部
> ⏱️ 11 小时 32 分
>
> 你最常看的：
> 🇯🇵 日腐
>
> 你本周最喜欢：
> 《XXX》
>
> 根据你的记录推荐：
> 《XXX》
>
> [查看推荐]

注意隐私设计：默认最好只发给本人，不要公开用户的成人内容观看记录。群排行榜如果涉及观看记录，建议默认匿名化或者让用户主动 opt-in。

你现在的项目结构其实非常适合做这些。

我会把整体能力重构为：

```text
services/
├─ emby/
│  ├─ account.py
│  ├─ activity.py
│  ├─ library.py
│  └─ playback.py
│
├─ recommendation/
│  ├─ ranking.py
│  ├─ personalized.py
│  └─ random.py
│
├─ media_request/
│  ├─ request.py
│  └─ voting.py
│
├─ engagement/
│  ├─ points.py
│  ├─ levels.py
│  ├─ streak.py
│  └─ missions.py
│
├─ referral/
│  ├─ invite.py
│  └─ rewards.py
│
├─ campaign/
│  └─ registration.py
│
└─ notification/
   ├─ new_media.py
   ├─ wishlist.py
   └─ digest.py
```

然后机器人首页不要再是传统的一堆命令：

```text
/register
/account
/info
```

而是做成一个“Emby 社区入口”：

```text
🎬 我的 Emby

🔥 今日热门       🆕 最新入库
🎲 随机看片       ❤️ 我的收藏

🔍 搜索影片       🙋 求片
📊 我的报告       👤 我的账号

🎟️ 开放注册       👥 邀请好友
```

如果只能选 5 个功能先做，我建议按这个顺序：

1. `/本周更新 + 热门榜单`
2. `求片 + 投票 + 上线通知`
3. `用户兴趣标签 + 个性推荐`
4. `注册预约 + 限量开放 + 倒计时`
5. `邀请统计 + 有效邀请奖励`

先不要急着开发签到、金币商城、复杂等级、抽奖。那些属于“游戏化外壳”，如果底层没有内容消费和互动循环，很容易变成机器人每天有人 `/签到`，但群依然没人交流。

你的核心增长飞轮应该是：

```text
             ┌────── 求片 / 推荐 ◄──────┐
             │                           │
             ▼                           │
新资源 → Bot 推送 → Emby观看 → 评分/讨论
  ▲                             │
  │                             ▼
  └──── 管理员选片 ◄──── 社区数据/投票
                                
用户观看
   ↓
个性推荐
   ↓
发现更多内容
   ↓
收藏/分享
   ↓
邀请同好
   ↓
新用户预约注册
   ↓
加入 Emby
   └──────────────────────► 循环
```

另外有一个关键指标：不要把“Telegram 消息数量”当第一 KPI。

你的核心指标建议是：

```text
新用户注册转化率
注册后 24h 首次播放率
7 日活跃观看用户
30 日留存
人均周播放次数
推荐点击率
求片参与人数
群投票参与率
有效邀请率
沉默用户召回率
```

例如真正值得关注的是：

```text
本周注册       100
成功进入Emby    91%
24h首次观看      76%
7日仍在观看      54%
30日仍活跃       37%
```

这比“群里今天 800 条消息”有意义得多。

如果让我给你的项目定一个产品定位，我不会继续把它做成：

> “一个可以申请 Emby 账号的 Telegram Bot”

而会做成：

> **“围绕 BL / 成人向男同影视内容的 Telegram + Emby 私域影视社区系统。”**

机器人承担用户系统、兴趣画像、推荐、求片、活动、通知、邀请和数据；Emby只承担真正的媒体消费。

这样扩张才有飞轮，而不是每次靠管理员手动开放注册拉一波人，然后重新沉寂。






























我目前有一个关于bl影视和gv的emby服务器 ，有电报群组以及机器人，我目前在基于机器人开发emby gv 的元数据补充，每次加新的数据源，我会把搜索结果和详细项目的页面html 保存到fixture目录下，然后写代码，但是每次开启新对话适配数据源，代码不好规范，有的字段没解析出来，，下面是初拟的代码规范，，更重要的是代码写好之后我怎么方便的查看解析器根据我本地的html 在搜索结果和详细页面分别解析出来的每个字段是什么，我来判断是不是我想要的
分层职责：

| 层 | 位置 | 职责 |
|----|------|------|
| HTTP 路由 | `bot/api/routes/emby_metadata.py` | 接收前端请求，编排业务，返回 JSON |
| 抓取业务 | `bot/services/emby_metadata/` | 数据源适配器、匹配策略、候选模型 |
| Emby 调用 | `bot/core/emby.py`（EmbyClient） | 读取条目、更新元数据、上传封面 |
| 配置 | `bot/core/config.py`（settings） | Emby 地址/API Key、数据源白名单 |
| 前端 | `web/src/` | React + shadcn/ui 管理界面 |

### 4.2 技术选型

- 后端：Python + FastAPI（**复用 `bot/api/`，不用 Flask**）。
- HTTP：复用 `bot/utils/http.py` 的 `HttpClient`（EmbyClient 已依赖它）。
- HTML 解析：BeautifulSoup4，仅处理允许访问的公开页面。
- 前端：React + shadcn/ui（当前阶段只确定技术栈，不实现前端）。
- 配置：复用 `bot/core/config.py` 的 `settings`，从根 `.env` 加载。API Key 只在 `.env`，`.env.example` 仅模板。
- 日志：复用 `loguru`，按时间记录到本地日志文件。

## 5. 核心模块

### 5.1 Emby 客户端（`bot/core/emby.py`）

复用现有 `EmbyClient`，按需补全以下能力：

| 能力 | 方法 | Emby 端点 | 现状 |
|------|------|-----------|------|
| 测试连接 | `get_system_info()` | `GET /System/Info` | 待补 |
| 获取用户列表 | `get_users()` | `GET /Users/Query` | 已有 |
| 获取电影列表 | `get_items(ids, user_id=...)` | `GET /Items` | 已有 |
| 获取完整条目 | `get_item(user_id, item_id)` | `GET /Users/{UserId}/Items/{Id}` | 已有 |
| 更新元数据 | `update_item(item_id, item_data)` | `POST /Items/{ItemId}` | 待补 |
| 上传 Item 封面 | `upload_item_image(item_id, image_data, image_type)` | `POST /Items/{ItemId}/Images/{Type}` | 待补 |
| 上传用户头像 | `upload_user_image(...)` | `POST /Users/{Id}/Images/{Type}` | 已有（非本功能用） |

更新前必须先读取完整 DTO，尽量只修改明确需要更新的字段，避免覆盖 Emby 内部字段。

### 5.2 数据源适配器（`bot/services/emby_metadata/`）

目录职责：

```text
bot/services/emby_metadata/
├─ models.py                  # Pydantic 候选模型和 Emby 可写字段
├─ matching.py                # 番号提取、规范化和候选置信度
├─ errors.py                  # 数据源网络、HTTP、解析错误
├─ auth/cookie_manager.py     # 读取本地 Cookie 配置
├─ parser/ck_download.py      # 只解析搜索结果页和详情页 HTML
├─ sources/base.py            # 数据源抽象接口
└─ sources/ck_download.py     # HTTP 请求、Cookie 和搜索流程编排
```

`parser/` 不发起网络请求，`sources/` 不直接处理 HTML 选择器。这样可以直接用保存的 fixture 验证页面解析，也可以单独替换请求层。

统一输出内部元数据模型 `MetadataCandidate`（pydantic）：

```text
MetadataCandidate
- source / source_id / category
- product_number
- title / original_title
- sort_name / forced_sort_name
- overview / year / release_date
- genres / studios / people / labels
- external_ids / poster_url
- runtime_minutes / confidence / raw_url
```

每个数据源独立实现搜索和详情解析，不能让 Web 层依赖具体网站 HTML 结构。媒体库固定映射为国产（`domestic`）、日韩（`japanese_korean`）、欧美（`western`），按“媒体库 → 默认分类 → 分类内数据源”路由，禁止跨分类调用。首个适配器 `ck_download` 属于日韩分类。当前仅支持关键词搜索，向 `/product/search` 发送 POST 表单（`kw`、`kw_opt=1`、`only_nm=0`）；详情页简介只读取 `.intro_text`，演员读取 `.prod_category` 的“出演モデル”，封面兼容 `.title_photo` 和 `.set_photo` 两种结构并固定选择 `{source_id}_1.jpg`。Cookie 从 `bot/config/cookies.toml` 读取，文件已加入 Git 忽略。
# Emby 元数据数据源开发规范

> 适用范围：`bot/services/emby_metadata/` 下的所有数据源。本文定义新增、修复和重构数据源时的唯一结构约束；与旧的“每个 source 完全独立”表述冲突时，以本文为准。

## 1. 目标和边界

一个数据源只负责“本站差异”，公共问题只能实现一次。代码必须同时满足：

- 搜索页只返回轻量 `MetadataSearchResult`，不为了补字段而逐条请求详情页。
- 详情页只返回完整 `MetadataCandidate`，所有字段可回溯到 fixture 或来源页面节点。
- 网络协议、重试、超时、浏览器请求头、Cookie、302、SSL 和图片请求与 HTML selector 分离。
- 来源专属的 URL、请求参数、页面层级、字段语义和特殊番号规则不被“通用化”猜测。

`ck-download` 的 parser/source 分层是正确方向，但不应复制它的私有清洗、日期、价格、图片、请求重试代码到每个新文件。

## 2. 固定目录与职责

```text
bot/services/emby_metadata/
├── models.py                 # 全部来源共用的 Pydantic 输出模型
├── errors.py                 # 全部来源共用的领域错误
├── parser/
│   ├── base.py               # 纯 HTML 解析公共能力；不得发网络请求
│   └── <source>.py           # 仅本站 selector、字段映射和 source_id 规则
├── sources/
│   ├── base.py               # HTTP、Session、超时、重试、图片请求头和错误转换
│   └── <source>.py           # 仅本站 URL、请求方法、表单、Cookie/SSL 特例和调用 parser
├── workbench.py              # 数据源注册、分类和番号路由；不放 selector
└── fixtures/<分类>/<source>/
    ├── search/<case>.html
    └── detail/<case>.html
```

允许复用：文本清洗、保留换行的简介清洗、绝对图片 URL、价格/日期解析、稳定去重、标准 HTTP 请求、图片请求头、错误转换、重试和 Session 生命周期。

禁止复用：本站 selector、字段中文/日文含义、来源 URL、POST 字段、Cookie 名称、Referer 规则、特殊 SSL、package/product 层级、番号路由和封面选择规则。

不要建立按“catalog”或“日韩站点”猜测行为的大杂烩文件。公共实现必须按职责命名，例如 `parser/base.py` 的 `clean_multiline()`，或 `sources/base.py` 的 `request_text()`；函数输入和输出必须明确，不能藏来源分支。

## 3. 新增数据源的必经流程

1. 收集证据：保存用户提供的 search/detail HTML；记录浏览器 Network 的方法、原始和最终 URL、302 链、POST 表单、Cookie、Referer、图片域名、状态码和证书问题。
2. 建立字段表：为每个输出字段列出“页面节点、selector、清洗规则、模型字段、缺失时行为”。不在 HTML 中的字段一律为空，不猜测。
3. 实现 parser：先写 `parse_search_results(html, limit)`，再写 `parse_detail(html, source_id)`；两者只接受 HTML，不创建 Session、不访问网络。
4. 实现 source：用基础 HTTP 能力声明本站 `base_url`、默认请求头、请求方法、路径/表单和必要的 Cookie、302、SSL 特例；source 只把 HTML 交给 parser。
5. 注册路由：在 `workbench.py` 注册来源；仅把明确的番号前缀和 package 规则加入 `_source_for_product_number()`。
6. 完成 fixture 校对：打印搜索和详情的关键字段，与 HTML 逐项比对；再做语法、导入和 `git diff --check`。除非用户要求，不运行完整测试套件。
7. 更新文档：在 handoff 记录 URL 流程、字段映射、特殊番号、图片策略、已验证 fixture 和仍待线上联调的事项。

## 4. Parser 规范

每个 parser 必须具有类常量 `source_name`、`base_url`、`category`，以及有类型标注和 docstring 的两个公开入口：

```python
@classmethod
def parse_search_results(cls, html: str, limit: int = 10) -> list[MetadataSearchResult]:
    ...

@classmethod
def parse_detail(cls, html: str, source_id: str) -> MetadataCandidate:
    ...
```

- 搜索仅匹配正式作品卡片。标题只能来自标题节点；日期、价格、排行榜和导航不能拼进标题。
- 搜索必须填写 `source_id`、`title`、`detail_url`、绝对 `image_urls`；页面存在时再填写日期、价格和状态。
- 详情必须校验关键节点；缺少标题、不可用 source_id 或页面层级错误时抛出 `MetadataSourceParseError`，不能静默产出半成品。
- 字段映射固定为：厂家/制作方到 `studios`，演出者到 `people`，标签/系列/类型到 `tags`。仅在来源明确表达该语义时写入。
- 简介通过公共多行清洗保留段落和 `<br>`；不可把原页面段落压成一整坨，也不可把导航、购买提示、登录提示混入简介。
- 图片从正式卡片或详情主图区域获取，先 `.strip()` 再转绝对 URL；演员图片要写入 `MetadataPerson.image_url`。
- 详情的 `parse_report` 必须至少含 `source_html_fields`，并加入可校对的原始字段、package 子链接或来源特殊信息。

## 5. Source 与图片代理规范

每个 source 只声明其差异：

- `search()`：关键词校验、本站 GET/POST、跳转流程，随后调用 parser。
- `fetch_detail()`：本站详情路径，随后调用 parser。
- `image_headers()`：只有网站图片需要 Referer、Cookie 或特殊 Accept 时才覆盖。

公共 `MetadataSource` / HTTP 基类应统一提供：单一 `aiohttp.ClientSession` 生命周期、默认超时、有限重试、状态码到 `MetadataSourceHTTPError` 的转换、网络错误到 `MetadataSourceNetworkError` 的转换，以及请求文本解码。

- SSL 关闭只能由 source 明确声明，并且仅用于已证实证书链有问题的域名；绝不修改全局 TLS。
- 需要 Cookie 的来源只从 `CookieManager` 取得
- 302 有会话语义时，必须保留同一个 Session 和 Cookie；不能跳过中间搜索请求直接访问结果页。
- `/api/emby/metadata/images` 根据图片域名解析并使用对应 source 的图片请求头和 SSL 策略；候选 JSON 有 URL 不等于图片实际可用。

## 6. 编码与维护要求

- 统一 PEP 8、88 字符行宽、完整类型标注和公开对象 docstring；本项目新增或修改的注释、docstring 和错误说明一律使用中文。
- 禁止单行塞入多个语句、裸 `except`、无说明的 fallback selector 和复制粘贴的 `_request`、`_clean`、`_price`、`_date` 实现。
- 公共 helper 必须是无状态或显式接收配置；不能读取某个 source 的全局变量，更不能在 helper 内 `if source_name == ...`。
- 现有来源统一继承 `HttpMetadataSource`；新增来源不得重新实现 `_request`、`image_headers`、Cookie 注入或通用异常转换，除非来源存在无法由声明式属性表达的协议差异，并须在 handoff 说明原因。
- 新规则优先补充 fixture 和小型 parser 回归用例；每个 bug 修复都应记录“错误 selector/流程、真实结构、修复结果”。

## 7. ck-download 的后续整改清单

- 保留其 parser/source 分层、明确 source_id 校验、字段白名单、详情主图规则和简介过滤策略。
- 将可复用的文本、日期、价格、图片和 HTTP 重试能力迁入职责清晰的基础层，再删除其他 source 的重复实现；不得把 ck-download 的本站 selector 搬进公共层。
- 不保留 source 到 parser 的“兼容入口”；测试和调用方必须直接使用 `CkDownloadParser.parse_search_results()`、`CkDownloadParser.parse_detail()`，避免 source 同时承担网络和 HTML 解析职责。
- HTTP 基类应负责 Session 生命周期和重试；source 不应每次请求、每次重试都手工复制 `ClientSession` 创建逻辑。当前 `HttpMetadataSource` 已承接该职责，后续来源迁移时直接继承它。
- 公共化前必须先用现有 fixture 对 ck-download 和至少一个结构不同的数据源校验，避免“抽象”破坏本站差异。

## 8. 新数据源交付清单

- [ ] fixture 目录完整，search/detail HTML 均可定位。
- [ ] Network 流程、URL、POST、302、Cookie、Referer、SSL 和图片域名已记录。
- [ ] 搜索字段和详情字段已逐项与 fixture 校对。
- [ ] 无重复的通用清洗、HTTP、价格、日期或图片代码。
- [ ] source 专属差异未被放入公共 helper。
- [ ] 特殊番号、package/product 和封面规则已注册并记录。
- [ ] 图片代理实际携带正确的请求头和 SSL 策略。
- [ ] 已完成 fixture 抽样、`py_compile`、`git diff --check`，并更新 handoff。















你现在这套规范的主方向是对的，尤其是 `parser/` 与 `sources/` 分离、fixture 驱动、公共能力和站点差异分开这几条。真正容易导致“换个新对话后又写歪”的问题，主要还缺两层约束：

1. “字段为什么得到这个值”的可观测性。
2. “这个字段到底是没解析、页面没有，还是这个站点根本不提供”的明确状态。

我建议把 fixture 验收做成正式开发基础设施，而不是临时 `print()`。

最核心的效果应该是你每次执行一条命令：

```bash
python -m bot.services.emby_metadata.fixture_cli inspect ck_download ssis_123
```

终端直接看到类似：

```text
数据源: ck_download
CASE: ssis_123

SEARCH #1
────────────────────────────────────────────────────────────────────
字段             状态       解析值                         selector
source_id        OK         123456                        ...
title            OK         SSIS-123 XXXXX               .product-name a
detail_url       OK         https://...                   .product-name a[href]
image_urls       OK         https://.../123456_1.jpg      .title_photo img
release_date     OK         2024-03-21                    ...
price            MISSING    —                             .price
status           UNSUPPORTED —                            —

DETAIL
────────────────────────────────────────────────────────────────────
字段             状态       解析值
source_id        OK         123456
product_number   OK         SSIS-123
title            OK         XXXXX
original_title   MISSING    —
overview         OK         第一段...
                            第二段...
year             DERIVED    2024
release_date     OK         2024-03-21
studios          OK         ["S1 NO.1 STYLE"]
people           OK         ["演员A", "演员B"]
genres           MISSING    —
tags             OK         ["巨乳", "..."]
runtime_minutes  OK         120
poster_url       OK         https://.../123456_1.jpg
```

但这还不够。点开 HTML 报告时，每一个字段都应该能够看到：

```text
字段: people

状态:
PARSED

最终值:
["演员A", "演员B"]

页面原始值:
出演モデル
演员A
演员B

Selector:
.prod_category ...

清洗过程:
["演员A ", "演员B"] → trim → stable_unique

来源:
detail fixture

备注:
仅读取“出演モデル”分类，不读取“監督”
```

这样你才真正能审核 AI 写出来的 parser。

我会把你的架构再增加下面这部分。

```text
bot/services/emby_metadata/
├── models.py
├── errors.py
│
├── parser/
│   ├── base.py
│   └── <source>.py
│
├── sources/
│   ├── base.py
│   └── <source>.py
│
├── diagnostics/
│   ├── models.py           # FieldEvidence / ParseInspection
│   ├── fixture_runner.py   # fixture → parser
│   ├── report.py           # 终端/JSON/HTML 报告
│   └── compare.py          # expected 与实际比较
│
├── fixtures/
│   └── japanese_korean/
│       └── ck_download/
│           ├── cases.toml
│           ├── search/
│           │   └── ssis_123.html
│           ├── detail/
│           │   └── ssis_123.html
│           └── expected/
│               └── ssis_123.json
│
├── fixture_cli.py
└── workbench.py
```

其中 `diagnostics/` 是开发工具，绝不能承担业务解析。

最关键的是把你现在比较模糊的 `parse_report.source_html_fields` 正式模型化。

例如：

```python
class FieldParseStatus(StrEnum):
    PARSED = "parsed"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    DERIVED = "derived"
    INVALID = "invalid"
    UNTRACKED = "untracked"


class FieldEvidence(BaseModel):
    field: str
    status: FieldParseStatus

    selector: str | None = None

    raw_value: Any = None
    normalized_value: Any = None

    source_label: str | None = None
    note: str | None = None


class ParseInspection(BaseModel):
    source: str
    page_type: Literal["search", "detail"]
    source_id: str | None = None

    fields: dict[str, FieldEvidence]
    warnings: list[str] = []
```

这里我尤其建议增加 `UNTRACKED`。

这是防止“有的字段根本没解析出来”的关键。

比如 `MetadataCandidate` 一共有：

```text
source
source_id
category
product_number
title
original_title
sort_name
forced_sort_name
overview
year
release_date
genres
studios
people
labels
external_ids
poster_url
runtime_minutes
confidence
raw_url
```

fixture inspector 完成后，要自动对照模型字段。

如果 parser 根本没有报告 `original_title`，它不能简单显示：

```text
original_title = None
```

而应该显示：

```text
original_title
UNTRACKED
parser 没有声明这个字段如何处理
```

这和：

```text
original_title
MISSING
已经检查 .xxx 节点，但当前页面不存在
```

是两回事。

还有第三种：

```text
original_title
UNSUPPORTED
本站没有 original_title 这一语义字段
```

这样 AI 少写一个字段，你马上就能发现。

这也是我认为你当前规范最值得加强的地方：

> `None` 不能表达字段解析状态。

必须区分：

```text
PARSED
页面有，成功解析

MISSING
parser 明确检查了，但当前 fixture 没有

UNSUPPORTED
这个数据源明确没有这个字段

DERIVED
不是页面直接字段，例如 year 从 release_date 得出

INVALID
页面有，但格式无法正常解析

UNTRACKED
parser 根本没有处理这个字段
```

`UNTRACKED` 在 fixture 验收时应该直接判失败。

另外，我建议不要要求每个 parser 自己手写：

```python
parse_report["title"] = ...
parse_report["people"] = ...
```

否则过几个数据源之后，又会变成每个人一种格式。

应该由 `parser/base.py` 提供很小的、纯解析的 evidence helper。例如概念上：

```python
value = audit.text(
    field="title",
    node=node,
    selector=".product-title",
)
```

或者：

```python
audit.record(
    field="people",
    status=FieldParseStatus.PARSED,
    selector="...",
    raw_value=raw_people,
    normalized_value=people,
    source_label="出演モデル",
)
```

这里的 `audit` 不进行任何 selector 推断，只负责记录。

站点 parser 决定：

```text
找哪个 selector
字段是什么意思
怎么组合
是否允许 fallback
```

公共层只决定：

```text
怎么记录证据
怎么检查覆盖率
怎么生成报告
```

这样不会违反你“来源语义不能公共化”的原则。

对于 search 页面，我建议报告形式稍有不同，因为一张页面往往返回 10 个结果。

首先展示一个总表：

```text
#  source_id  product_number  title                date        image
1  12345      SSIS-123       XXXXX                2024-...    ✓
2  12346      SSIS-124       YYYYY                2024-...    ✓
3  12347      SSIS-125       ZZZZZ                —           ✓
```

然后允许：

```bash
python -m ... fixture_cli inspect ck_download ssis_123 --result 2
```

查看第二个结果每个字段的 Evidence。

HTML 报告则把每个搜索结果做成可展开区域。

还有一个非常重要的东西：图片不要只显示 URL。

你的 GV 元数据适配里，封面是非常容易“URL 看起来正确、实际上选错图片”的字段。

HTML inspection 页面应该直接：

```text
poster_url
https://example/.../123_1.jpg

[实际图片预览]
```

fixture 本身不需要联网时，可以默认只显示 URL；如果你明确开启：

```bash
--fetch-images
```

再通过对应 source 的 `image_headers()` 去请求图片。

这样还能顺便验证：

```text
Referer
Cookie
SSL
图片域名
```

而不会错误地让 parser 发网络请求。

我还非常建议给 fixture 增加一个很薄的 `cases.toml`。

例如：

```toml
[[case]]
name = "ssis_123"
keyword = "SSIS-123"
search = "search/ssis_123.html"
detail = "detail/ssis_123.html"
source_id = "123456"
search_result_index = 0
```

而不是只靠：

```text
search/1.html
detail/test.html
```

猜它们之间是什么关系。

这样每个 case 从搜索 → 搜索候选 → 详情，就是一条完整链路。

以后还有 package 类型，可以：

```toml
[[case]]
name = "package_xxx"
keyword = "XXX-001"
search = "search/package_xxx.html"
detail = "detail/package_xxx.html"
source_id = "abc"
kind = "package"
```

也不用改 inspector。

再往后一步，inspection 和测试最好不要是两套东西。

推荐你的实际开发循环固定成：

```text
保存 fixture
      ↓
实现 parser
      ↓
inspect
      ↓
人工逐字段审核
      ↓
approve
      ↓
生成 expected JSON
      ↓
以后自动 regression compare
```

例如：

```bash
python -m bot.services.emby_metadata.fixture_cli inspect \
    ck_download ssis_123
```

人工确认没问题后：

```bash
python -m bot.services.emby_metadata.fixture_cli approve \
    ck_download ssis_123
```

得到：

```text
fixtures/japanese_korean/ck_download/
└── expected/
    └── ssis_123.json
```

内容只保存最终业务值：

```json
{
  "search": [
    {
      "source_id": "123456",
      "title": "xxx",
      "detail_url": "https://...",
      "image_urls": ["https://..."]
    }
  ],
  "detail": {
    "source_id": "123456",
    "product_number": "SSIS-123",
    "title": "xxx",
    "overview": "xxx",
    "studios": ["xxx"],
    "people": [
      {
        "name": "演员A",
        "image_url": "https://..."
      }
    ],
    "poster_url": "https://..."
  }
}
```

以后 AI 改 parser，只要：

```bash
python -m bot.services.emby_metadata.fixture_cli check ck_download
```

输出：

```text
ck_download

PASS  ssis_123 search
FAIL  ssis_123 detail

people:
- expected: ["演员A", "演员B"]
+ actual:   ["演员A"]

poster_url:
  unchanged

overview:
  unchanged
```

这样 selector 改坏了，你不需要自己重新研究整个 HTML。

这里还有一个重要原则：

**不要一开始就让 AI 写 expected JSON。**

否则 AI parser 写错，然后 AI 又根据自己错误的 parser 生成 expected，就形成“错误验证错误”。

应该是：

```text
第一次：
HTML → parser → inspection → 你人工确认 → approve

以后：
HTML → parser → expected 自动比较
```

这对你的项目尤其重要。

对于你说的“每次开启新对话代码不好规范”，除了现有规范，我会进一步要求新数据源对话严格按照固定交付顺序，而不是直接让模型开始写代码：

```text
阶段 1：Fixture Evidence
阶段 2：Field Mapping
阶段 3：Parser
阶段 4：Fixture Inspection
阶段 5：Source HTTP
阶段 6：Regression
```

尤其要求 AI 在写 parser 前先输出内部字段映射，例如：

```text
DETAIL FIELD MAP

title
  selector: .product-title
  raw example: ...
  normalize: clean_text
  missing: ERROR

product_number
  selector: ...
  raw example: SSIS-123
  normalize: normalize_product_number
  missing: None

people
  parent: .prod_category
  semantic label: 出演モデル
  item selector: ...
  normalize: stable_unique
  missing: []

overview
  selector: .intro_text
  normalize: clean_multiline
  missing: None
```

你不认可这个表，就不进入实现阶段。

这比单纯给 Claude/Codex/ChatGPT 一篇很长的规范更有效，因为它强迫模型先理解页面结构。

你的规范里我还会修改一个术语问题。前面统一模型写的是：

```text
genres / studios / people / labels
```

后面的 parser 规范写成：

```text
标签/系列/类型到 tags
```

这里已经产生了一个潜在漂移。

必须只留下一个正式字段，比如确定：

```python
genres
studios
people
labels
```

那后面就不能出现 `tags`。

或者模型正式采用：

```python
genres
studios
people
tags
```

那全文就删除 `labels`。

这种“规范内部字段名字不一致”，正是新对话特别容易导致 parser 字段遗漏的原因之一。

还有 `MetadataSearchResult` 也应该明确写成正式 schema，不要只重点描述 `MetadataCandidate`。比如固定：

```python
MetadataSearchResult
- source
- source_id
- category
- product_number
- title
- detail_url
- image_urls
- release_date
- price
- status
```

哪些是 required，哪些 optional，必须直接定义清楚。

因此你的数据流最终应该是：

```text
                        ┌──────────────┐
fixture search.html ───▶│ SourceParser │
                        └──────┬───────┘
                               │
                 ┌─────────────┴──────────────┐
                 ▼                            ▼
      MetadataSearchResult[]          ParseInspection
                 │                            │
                 │                            ├── selector
                 │                            ├── raw
                 │                            ├── normalized
                 │                            ├── status
                 │                            └── warning
                 │
                 ▼
             人工审核


                        ┌──────────────┐
fixture detail.html ───▶│ SourceParser │
                        └──────┬───────┘
                               │
                 ┌─────────────┴──────────────┐
                 ▼                            ▼
       MetadataCandidate              ParseInspection
                 │                            │
                 └────────────┬───────────────┘
                              ▼
                       expected snapshot
                              │
                              ▼
                     后续 regression check
```

我认为这是最适合你目前项目的方案。它不需要现在做 React 管理页面，也不需要启动 FastAPI，纯本地 fixture 就能工作；以后如果做前端，“字段解析报告”这一整套结构也可以直接通过开发 API 输出给 React。

最终我会把新增数据源的验收条件从你现在的：

> “打印搜索和详情的关键字段，与 HTML 逐项比对”

升级成：

> **模型中的所有可解析字段必须进入 Field Evidence；fixture inspection 中不得存在 `UNTRACKED` 字段。每个非空字段必须能展示 selector/语义来源、raw value 和 normalized value；每个空字段必须明确为 `MISSING` 或 `UNSUPPORTED`。人工确认后生成 expected snapshot，用于后续 parser regression。**

这一条实际上能解决你说的两个核心问题：一是新对话写出来的 parser 不统一，二是有字段没解析你却不容易发现。




具体可以直接按下面这个 V1 落地。核心目标只有一个：

> 保存 `search.html + detail.html` 后，执行一条命令，浏览器自动打开报告，把两个页面解析出的所有字段、selector、原始值、最终值、缺失状态全部列出来。

先不要做前端，也不要依赖 FastAPI。

### 1. 最终目录

```text
bot/services/emby_metadata/
├── models.py
├── parser/
│   ├── base.py
│   └── ck_download.py
├── sources/
│   ├── base.py
│   └── ck_download.py
│
├── diagnostics/
│   ├── __init__.py
│   ├── models.py
│   ├── fixture_runner.py
│   └── report.py
│
├── fixture_cli.py
│
└── fixtures/
    └── japanese_korean/
        └── ck_download/
            ├── cases.toml
            ├── search/
            │   └── ssis_123.html
            └── detail/
                └── ssis_123.html
```

以后你添加新站，只需要：

```text
parser/new_site.py
sources/new_site.py

fixtures/japanese_korean/new_site/
├── cases.toml
├── search/
└── detail/
```

而 diagnostics 完全不用复制。

---

## 2. 先定义“字段解析证据”

新建：

```text
bot/services/emby_metadata/diagnostics/models.py
```

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class FieldParseStatus(StrEnum):
    """字段解析状态。"""

    PARSED = "parsed"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    DERIVED = "derived"
    INVALID = "invalid"
    UNTRACKED = "untracked"


class FieldEvidence(BaseModel):
    """单个字段的 HTML 解析证据。"""

    status: FieldParseStatus
    selector: str | None = None
    raw_value: Any = None
    normalized_value: Any = None
    source_label: str | None = None
    note: str | None = None


class ParseReport(BaseModel):
    """一次搜索结果或详情解析的字段报告。"""

    page_type: Literal["search", "detail"]
    fields: dict[str, FieldEvidence] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    def record(
        self,
        field: str,
        *,
        status: FieldParseStatus,
        selector: str | None = None,
        raw_value: Any = None,
        normalized_value: Any = None,
        source_label: str | None = None,
        note: str | None = None,
    ) -> None:
        """记录字段解析证据。"""

        self.fields[field] = FieldEvidence(
            status=status,
            selector=selector,
            raw_value=raw_value,
            normalized_value=normalized_value,
            source_label=source_label,
            note=note,
        )
```

这里最重要的是：

```text
PARSED
MISSING
UNSUPPORTED
DERIVED
INVALID
UNTRACKED
```

特别是 `UNTRACKED`。

它意味着：

> MetadataCandidate 有这个字段，但你的 parser 连“我没解析它”都没声明。

这就能抓住你现在最头疼的“AI 漏写字段”。

---

## 3. 给两个输出模型增加 parse_report

假设你现在 `models.py` 大致有：

```python
class MetadataSearchResult(BaseModel):
    ...
```

和：

```python
class MetadataCandidate(BaseModel):
    ...
```

增加：

```python
from pydantic import Field

from .diagnostics.models import ParseReport


class MetadataSearchResult(BaseModel):
    source: str
    source_id: str
    category: str

    product_number: str | None = None
    title: str

    detail_url: str
    image_urls: list[str] = Field(default_factory=list)

    release_date: str | None = None
    price: str | None = None
    status: str | None = None

    parse_report: ParseReport | None = Field(
        default=None,
        exclude=True,
    )
```

详情同理：

```python
class MetadataCandidate(BaseModel):
    source: str
    source_id: str
    category: str

    product_number: str | None = None
    title: str
    original_title: str | None = None

    sort_name: str | None = None
    forced_sort_name: str | None = None

    overview: str | None = None
    year: int | None = None
    release_date: str | None = None

    genres: list[str] = Field(default_factory=list)
    studios: list[str] = Field(default_factory=list)
    people: list[MetadataPerson] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)

    external_ids: dict[str, str] = Field(default_factory=dict)

    poster_url: str | None = None
    runtime_minutes: int | None = None

    confidence: float | None = None
    raw_url: str | None = None

    parse_report: ParseReport | None = Field(
        default=None,
        exclude=True,
    )
```

`exclude=True` 很重要。

所以正式 API：

```python
candidate.model_dump()
```

不会把这些调试信息发给 Emby 或前端。

但是 fixture 工具仍然能：

```python
candidate.parse_report
```

读取。

---

## 4. parser 具体怎么写

以 `ck_download` 为例。

以前你可能是：

```python
title = clean_text(soup.select_one(...))
```

现在改成：

```python
report = ParseReport(page_type="detail")
```

然后每解析一个字段都留证据。

例如：

```python
from bs4 import BeautifulSoup

from ..diagnostics.models import (
    FieldParseStatus,
    ParseReport,
)
from ..models import MetadataCandidate
from .base import MetadataParser


class CkDownloadParser(MetadataParser):
    """CK Download HTML 解析器。"""

    source_name = "ck_download"
    base_url = "https://example.com"
    category = "japanese_korean"

    @classmethod
    def parse_detail(
        cls,
        html: str,
        source_id: str,
    ) -> MetadataCandidate:
        """解析作品详情页。"""

        soup = BeautifulSoup(html, "html.parser")
        report = ParseReport(page_type="detail")

        report.record(
            "source",
            status=FieldParseStatus.DERIVED,
            normalized_value=cls.source_name,
            note="parser 类常量",
        )

        report.record(
            "source_id",
            status=FieldParseStatus.DERIVED,
            normalized_value=source_id,
            note="详情请求参数",
        )

        report.record(
            "category",
            status=FieldParseStatus.DERIVED,
            normalized_value=cls.category,
            note="parser 类常量",
        )

        title_selector = ".product_title"
        title_node = soup.select_one(title_selector)

        if title_node is None:
            report.record(
                "title",
                status=FieldParseStatus.MISSING,
                selector=title_selector,
                note="详情页缺少标题节点",
            )
            raise MetadataSourceParseError("详情页缺少标题")

        raw_title = title_node.get_text(" ", strip=False)
        title = cls.clean_text(raw_title)

        report.record(
            "title",
            status=FieldParseStatus.PARSED,
            selector=title_selector,
            raw_value=raw_title,
            normalized_value=title,
        )

        overview_selector = ".intro_text"
        overview_node = soup.select_one(overview_selector)

        if overview_node:
            raw_overview = overview_node.get_text(
                "\n",
                strip=False,
            )
            overview = cls.clean_multiline(
                raw_overview,
            )

            report.record(
                "overview",
                status=FieldParseStatus.PARSED,
                selector=overview_selector,
                raw_value=raw_overview,
                normalized_value=overview,
            )
        else:
            overview = None

            report.record(
                "overview",
                status=FieldParseStatus.MISSING,
                selector=overview_selector,
            )

        # 本站明确没有 original_title。
        report.record(
            "original_title",
            status=FieldParseStatus.UNSUPPORTED,
            note="本站页面未提供独立原始标题字段",
        )

        candidate = MetadataCandidate(
            source=cls.source_name,
            source_id=source_id,
            category=cls.category,
            title=title,
            overview=overview,
            parse_report=report,
        )

        return candidate
```

注意一个原则：

不要这样：

```python
report.record("people", ...)
```

然后随便写一个 selector。

必须是 parser 实际用了什么 selector，就记录什么。

所以：

```text
HTML selector
↓
raw value
↓
清洗
↓
normalized value
↓
MetadataCandidate
```

完全连起来。

---

# 5. 演员这种复杂字段怎么记录

这个更重要。

假设 HTML 是：

```html
<div class="prod_category">
    <span class="label">出演モデル</span>
    <a href="/model/1">女优 A</a>
    <a href="/model/2">女优 B</a>
</div>
```

不要只记：

```text
people = ["女优 A", "女优 B"]
```

应该：

```python
people_selector = ".prod_category"

raw_people: list[str] = []
people: list[MetadataPerson] = []

for section in soup.select(people_selector):
    label_node = section.select_one(".label")

    if label_node is None:
        continue

    label = cls.clean_text(
        label_node.get_text(" ", strip=True),
    )

    if label != "出演モデル":
        continue

    for actor_node in section.select("a"):
        raw_name = actor_node.get_text(
            " ",
            strip=False,
        )

        name = cls.clean_text(raw_name)

        if not name:
            continue

        raw_people.append(raw_name)

        people.append(
            MetadataPerson(
                name=name,
            )
        )

report.record(
    "people",
    status=(
        FieldParseStatus.PARSED
        if people
        else FieldParseStatus.MISSING
    ),
    selector='.prod_category[label="出演モデル"] a',
    raw_value=raw_people,
    normalized_value=[
        person.model_dump()
        for person in people
    ],
    source_label="出演モデル",
)
```

于是你的报告能明确告诉你：

```text
字段
people

语义来源
出演モデル

selector
.prod_category ... a

HTML 原始值
[
  "女优 A ",
  " 女优 B"
]

最终值
[
  {"name": "女优 A"},
  {"name": "女优 B"}
]
```

你一眼就知道 AI 有没有把导演也解析进演员。

---

# 6. fixture 的 cases.toml

例如：

```text
fixtures/japanese_korean/ck_download/cases.toml
```

内容：

```toml
[[case]]
name = "ssis_123"
keyword = "SSIS-123"

search = "search/ssis_123.html"
detail = "detail/ssis_123.html"

source_id = "123456"
```

以后增加一个 fixture：

```toml
[[case]]
name = "ssis_456"
keyword = "SSIS-456"

search = "search/ssis_456.html"
detail = "detail/ssis_456.html"

source_id = "567890"
```

不用改任何 Python。

---

# 7. fixture_runner

新建：

```text
diagnostics/fixture_runner.py
```

核心逻辑非常简单：

```python
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel


@dataclass(slots=True)
class FixtureCase:
    """一个完整的搜索/详情 fixture 用例。"""

    name: str
    keyword: str
    search: str
    detail: str
    source_id: str


@dataclass(slots=True)
class FixtureInspection:
    """fixture 解析结果。"""

    case: FixtureCase
    search_results: list[Any]
    detail_result: Any


def load_cases(
    fixture_root: Path,
) -> dict[str, FixtureCase]:
    """读取数据源 fixture case 配置。"""

    path = fixture_root / "cases.toml"

    with path.open("rb") as file:
        data = tomllib.load(file)

    cases: dict[str, FixtureCase] = {}

    for item in data.get("case", []):
        case = FixtureCase(**item)
        cases[case.name] = case

    return cases


def add_untracked_fields(
    model: BaseModel,
) -> None:
    """把 parser 没有声明的字段标记为 UNTRACKED。"""

    from .models import (
        FieldEvidence,
        FieldParseStatus,
    )

    report = getattr(
        model,
        "parse_report",
        None,
    )

    if report is None:
        return

    for field_name in type(model).model_fields:
        if field_name == "parse_report":
            continue

        if field_name in report.fields:
            continue

        report.fields[field_name] = FieldEvidence(
            status=FieldParseStatus.UNTRACKED,
            normalized_value=getattr(
                model,
                field_name,
            ),
            note="parser 未声明该字段的来源或缺失策略",
        )


def inspect_fixture(
    *,
    parser_class: type,
    fixture_root: Path,
    case_name: str,
) -> FixtureInspection:
    """使用纯本地 HTML 执行 parser。"""

    cases = load_cases(fixture_root)

    case = cases[case_name]

    search_html = (
        fixture_root / case.search
    ).read_text(
        encoding="utf-8",
    )

    detail_html = (
        fixture_root / case.detail
    ).read_text(
        encoding="utf-8",
    )

    search_results = (
        parser_class.parse_search_results(
            search_html,
            limit=50,
        )
    )

    detail_result = parser_class.parse_detail(
        detail_html,
        source_id=case.source_id,
    )

    for result in search_results:
        add_untracked_fields(result)

    add_untracked_fields(detail_result)

    return FixtureInspection(
        case=case,
        search_results=search_results,
        detail_result=detail_result,
    )
```

这段代码最关键的是：

```python
add_untracked_fields()
```

如果 AI 新写 parser 时忘记：

```python
runtime_minutes
```

你的报告直接出现：

```text
runtime_minutes
UNTRACKED
```

而不是安静地：

```text
runtime_minutes = None
```

---

# 8. 最关键：生成浏览器报告

我推荐你不要只看 Terminal。

直接生成：

```text
.dev/
└── metadata_reports/
    └── ck_download/
        └── ssis_123.html
```

然后自动打开浏览器。

页面大致：

```text
CK DOWNLOAD
Fixture: ssis_123


SEARCH RESULTS

#1 SSIS-123
--------------------------------------------

source_id
✓ PARSED
最终值: 123456

title
✓ PARSED
selector: .product_title a

原始:
  SSIS-123   XXXXX

最终:
  SSIS-123 XXXXX


image_urls
✓ PARSED

原始:
  /images/123456_1.jpg

最终:
  https://xxxx/images/123456_1.jpg


DETAIL

title
✓ PARSED

product_number
✓ PARSED

overview
✓ PARSED

people
✓ PARSED

studios
✓ PARSED

runtime_minutes
⚠ UNTRACKED

original_title
○ UNSUPPORTED
```

颜色：

```text
绿色  PARSED
蓝色  DERIVED
灰色  UNSUPPORTED
黄色  MISSING
红色  INVALID
红色  UNTRACKED
```

特别是：

```text
UNTRACKED
```

必须非常显眼。

---

# 9. report.py 不需要引入 React

完全可以生成静态 HTML。

核心逻辑：

```python
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _format_value(value: Any) -> str:
    if value is None:
        return "—"

    if isinstance(
        value,
        (dict, list),
    ):
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    return str(value)


def _render_field(
    name: str,
    evidence: Any,
) -> str:
    raw = html.escape(
        _format_value(
            evidence.raw_value,
        )
    )

    normalized = html.escape(
        _format_value(
            evidence.normalized_value,
        )
    )

    selector = html.escape(
        evidence.selector or "—"
    )

    note = html.escape(
        evidence.note or ""
    )

    return f"""
    <section class="field">
        <header>
            <strong>{html.escape(name)}</strong>
            <span class="status {evidence.status.value}">
                {evidence.status.value.upper()}
            </span>
        </header>

        <div>
            <b>Selector</b>
            <pre>{selector}</pre>
        </div>

        <div>
            <b>原始值</b>
            <pre>{raw}</pre>
        </div>

        <div>
            <b>最终值</b>
            <pre>{normalized}</pre>
        </div>

        <div class="note">
            {note}
        </div>
    </section>
    """


def write_html_report(
    inspection: Any,
    output_path: Path,
) -> None:
    """输出本地 fixture 解析报告。"""

    detail_report = (
        inspection.detail_result.parse_report
    )

    detail_fields = "\n".join(
        _render_field(
            name,
            evidence,
        )
        for name, evidence
        in detail_report.fields.items()
    )

    document = f"""
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">

<title>
Metadata Fixture Inspection
</title>

<style>
body {{
    max-width: 1200px;
    margin: 40px auto;
    padding: 0 24px;
    font-family: sans-serif;
}}

.field {{
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 16px;
    margin: 12px 0;
}}

.field header {{
    display: flex;
    justify-content: space-between;
}}

pre {{
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}}

.status {{
    font-weight: bold;
}}

.parsed {{
    color: green;
}}

.derived {{
    color: blue;
}}

.missing {{
    color: #b7791f;
}}

.unsupported {{
    color: #666;
}}

.invalid,
.untracked {{
    color: red;
}}
</style>
</head>

<body>

<h1>Fixture Inspection</h1>

<p>
Case:
<strong>{html.escape(inspection.case.name)}</strong>
</p>

<h2>DETAIL</h2>

{detail_fields}

</body>
</html>
"""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        document,
        encoding="utf-8",
    )
```

第一版甚至可以只把 Detail 做出来。

等 Detail 好用了，再把 search results 同样加入。

---

# 10. 最后做 CLI

新建：

```text
bot/services/emby_metadata/fixture_cli.py
```

最终希望你使用：

```bash
python -m bot.services.emby_metadata.fixture_cli \
    inspect ck_download ssis_123
```

或者：

```bash
python -m bot.services.emby_metadata.fixture_cli \
    inspect ck_download ssis_123 --open
```

CLI 大概：

```python
from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from .diagnostics.fixture_runner import (
    inspect_fixture,
)
from .diagnostics.report import (
    write_html_report,
)
from .parser.ck_download import (
    CkDownloadParser,
)


PARSERS = {
    "ck_download": CkDownloadParser,
}


FIXTURE_BASE = (
    Path(__file__).parent
    / "fixtures"
)


SOURCE_CATEGORIES = {
    "ck_download": "japanese_korean",
}


def main() -> None:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    inspect_parser = subparsers.add_parser(
        "inspect",
    )

    inspect_parser.add_argument(
        "source",
    )

    inspect_parser.add_argument(
        "case",
    )

    inspect_parser.add_argument(
        "--open",
        action="store_true",
    )

    args = parser.parse_args()

    if args.command != "inspect":
        return

    parser_class = PARSERS[args.source]

    category = SOURCE_CATEGORIES[
        args.source
    ]

    fixture_root = (
        FIXTURE_BASE
        / category
        / args.source
    )

    inspection = inspect_fixture(
        parser_class=parser_class,
        fixture_root=fixture_root,
        case_name=args.case,
    )

    output = (
        Path(".dev")
        / "metadata_reports"
        / args.source
        / f"{args.case}.html"
    )

    write_html_report(
        inspection,
        output,
    )

    print(
        f"报告已生成: {output}"
    )

    if args.open:
        webbrowser.open(
            output.resolve().as_uri()
        )


if __name__ == "__main__":
    main()
```

于是：

```bash
python -m bot.services.emby_metadata.fixture_cli \
  inspect ck_download ssis_123 --open
```

浏览器直接打开。

---

# 11. 你每天实际开发新数据源就变成这样

例如新加：

```text
gaydata
```

先保存：

```text
fixtures/western/gaydata/
├── cases.toml
├── search/
│   └── abc123.html
└── detail/
    └── abc123.html
```

然后先写：

```python
GayDataParser.parse_search_results()
GayDataParser.parse_detail()
```

此时完全不写：

```text
source HTTP
Cookie
Emby
FastAPI
```

然后执行：

```bash
python -m bot.services.emby_metadata.fixture_cli \
  inspect gaydata abc123 --open
```

你看到：

```text
title
PARSED
xxxxx

product_number
PARSED
ABC-123

overview
PARSED
xxxxx

studios
PARSED
["XXX"]

people
PARSED
["AAA", "BBB"]

genres
UNTRACKED     ← AI 漏写

labels
PARSED
["裸", "xxx"]

release_date
INVALID       ← 找到了，但日期解析错误

runtime_minutes
MISSING       ← parser 找过，fixture 没有

original_title
UNSUPPORTED   ← 本站本来就没有

poster_url
PARSED
https://...
```

这时候你就能非常快地告诉新对话里的 AI：

> `genres` 不允许 UNTRACKED，HTML 中 xxx 区域就是类型，请修正。
> `release_date` 页面原始值已经抓对，但是 normalization 错了。
> `runtime_minutes` 当前 fixture 确实不存在，不需要改。

它不会再重新瞎猜整个网页。

---

# 12. 我还建议再加一个硬性检查

最后 fixture inspection 输出：

```text
FIELD COVERAGE

Detail:
18 / 19 tracked

ERROR:
genres = UNTRACKED
```

只要存在：

```text
UNTRACKED
INVALID
```

命令退出码就为 `1`。

这样以后 AI 改完代码，你可以要求它必须运行：

```bash
python -m bot.services.emby_metadata.fixture_cli \
  inspect ck_download ssis_123
```

必须：

```text
exit code = 0
```

才能算交付。

`MISSING` 和 `UNSUPPORTED` 可以通过。

`UNTRACKED` 和 `INVALID` 不通过。

---

你当前规范里那一句：

> “打印搜索和详情的关键字段，与 HTML 逐项比对”

我建议直接废掉，改成：

> `fixture_cli inspect` 必须枚举 `MetadataSearchResult` / `MetadataCandidate` 的全部业务字段。每个字段必须明确为 `PARSED / DERIVED / MISSING / UNSUPPORTED / INVALID` 之一，不允许存在 `UNTRACKED`。`PARSED` 字段必须记录 selector、raw_value 和 normalized_value。Fixture 验收存在 `UNTRACKED` 或 `INVALID` 时失败。

这是一个非常关键的硬约束。

下一步再加 `approve` 和 `check`，就能做到你人工确认一次之后，以后 AI 改 selector 自动告诉你“哪个字段从什么值变成什么值”。这会比一开始做管理前端更有价值。
