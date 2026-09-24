# 桜色男孩 Android App 开发交接文档

> 文档状态：当前设计，可作为新 Android 项目的实现依据  
> 更新时间：2026-09-25  
> 目标设备：小米 14 / HyperOS  
> 使用范围：仅供所有者个人使用，暂不发布应用市场

## 1. 给新项目开发者的任务说明

请创建一个新的原生 Android 项目，实现名为 **“桜色男孩”** 的个人通知客户端。

该 App 与现有 Python 项目 `telegram-bot-template-donBarbos` 配套使用。Python 项目负责长期运行、监控外部事件并生成通知；Android App 只负责稳定连接服务器、接收通知、展示通知并回传送达状态。

以下决策已经确定，不要在未发现技术阻塞时重新讨论：

1. App 展示名称为 `桜色男孩`。
2. 英文项目标识、群组关联标识使用 `lustfulboy`。
3. 建议包名为 `com.alviss.lustfulboy`。
4. App 仅供所有者个人侧载使用，首期不考虑应用商店发布、多租户和公共注册。
5. 不接入 Mi Push、小米推送或其他手机厂商推送服务。
6. 首期不要求接入 FCM；如以后确认 Google Play 服务长期稳定，可将 FCM 作为备用通道，而不是当前必需项。
7. App 不在手机本地监控 Instagram，也不在后台自行轮询 Instagram。
8. 通知来源必须可扩展，不能把底层协议写死为 Instagram Story。Instagram Story 只是第一个业务事件。
9. App 的新代码注释、错误提示和项目文档使用中文。

## 2. 项目位置与技术选型

建议将 Android 项目建立为独立目录和独立 Git 仓库：

```text
D:\Projects\Python\telegram-bot-template-donBarbos  # Python 服务端
D:\Projects\Android\lustfulboy-android              # Android 客户端
```

Android 项目建议配置：

```text
项目名称：lustfulboy-android
App 名称：桜色男孩
包名：com.alviss.lustfulboy
语言：Kotlin
界面：Jetpack Compose
构建脚本：Gradle Kotlin DSL
项目模板：Empty Activity
最低版本：优先兼容 Android 8.0 及以上；若依赖产生冲突，可按实际需求提高
目标版本：使用开发时 Android Studio 支持的最新稳定目标版本
```

依赖版本不要直接照抄本文档中的日期或猜测版本号。创建项目时使用 Android Studio 和官方文档提供的最新稳定版本，并锁定到 Gradle Version Catalog。

## 3. 现有 Python 项目事实

现有服务端项目具备以下基础：

- Python 3.10 及以上。
- Aiogram 3 异步 Telegram Bot。
- FastAPI API 服务。
- SQLAlchemy 异步数据库访问。
- MySQL 数据库。
- Alembic 正式数据库迁移。
- Docker Compose 部署方式。
- 已有统一的机器人启动、后台任务跟踪和安全关闭机制。

当前 Android 通知接口、设备表、WebSocket 服务尚未实现。新 Android 项目可以先完成本地通知和模拟 WebSocket 客户端，服务端接口随后在原 Python 项目中按本文契约实现。

不要依赖当前用于 Telegram 测试的“每 5 秒给所有者发消息”临时代码。该代码仅用于验证 Telegram 通知，测试结束后应删除，与 Android 通知系统无关。

## 4. 总体架构

```text
外部事件源
例如 Instagram Story
        │
        ▼
Python 监控服务
        │ 创建统一通知事件并写入数据库
        ▼
移动通知服务
        ├─────────────► Telegram（保留完整媒体和备用通知）
        │
        └─ WebSocket ─► 桜色男孩 Android App
                              │
                              ├─ 立即回传 received ACK
                              ├─ 显示锁屏/横幅/声音/振动通知
                              └─ 用户点击后回传 opened ACK

断线或重启
Android App ── REST 补拉 ──► 未确认通知事件
```

### 4.1 为什么采用前台长连接

不使用 Mi Push 或其他系统级推送后，普通后台进程无法保证长期存活。因此首期采用用户明确开启的前台服务维护 WebSocket 长连接。

前台服务必须始终展示一条低打扰常驻通知，例如：

```text
桜色男孩正在等待通知
连接状态：已连接
```

该通知不能与真正的业务通知共用通知渠道。

前台服务建议声明与远程消息相匹配的服务类型；在 Android 14 及以上实现时，应依据官方最新规则评估 `remoteMessaging`，并声明相应权限。若最新平台规则认为当前用途不适配该类型，应按官方允许的服务类型调整，不能通过伪装成电话、闹钟、定位或媒体播放服务绕过限制。

### 4.2 可及性边界

该方案在小米 14 上可以获得较高可及性，但不能承诺绝对必达：

- 用户“强行停止”App 后，普通应用无法自行恢复。
- 用户关闭通知权限后，App 无法展示业务通知。
- HyperOS 拒绝自启动、限制后台运行或清理进程时，长连接可能中断。
- 手机断网时无法实时收到，但联网后必须通过 REST 补拉遗漏事件。
- 服务器停止运行时不会产生任何新通知。
- 普通通知不保证强制点亮屏幕；首期使用高重要性锁屏和横幅通知，不滥用全屏通知。

## 5. Android 端模块设计

建议目录结构：

```text
app/src/main/java/com/alviss/lustfulboy/
├── app/
│   ├── LustfulBoyApplication.kt
│   └── MainActivity.kt
├── core/
│   ├── model/
│   ├── network/
│   ├── security/
│   └── util/
├── data/
│   ├── api/
│   ├── local/
│   ├── repository/
│   └── websocket/
├── notification/
│   ├── NotificationChannels.kt
│   └── NotificationDispatcher.kt
├── service/
│   └── NotificationConnectionService.kt
├── receiver/
│   └── BootReceiver.kt
└── feature/
    ├── home/
    ├── pairing/
    ├── history/
    └── settings/
```

### 5.1 第一版页面

第一版只需要四个页面或功能区域：

1. **配对页面**
   - 扫描服务端生成的二维码或输入一次性配对码。
   - 显示服务器地址，但不在日志中输出认证令牌。

2. **主页**
   - 显示服务器连接状态。
   - 显示最近一次成功连接、最近一次收到通知的时间。
   - 提供“启动连接”“停止连接”“发送本地测试通知”按钮。

3. **通知历史**
   - 显示最近收到的通知。
   - 按 `event_id` 去重。
   - 显示收到时间、事件时间和点击状态。

4. **设置页**
   - 打开系统通知设置。
   - 打开电池优化设置。
   - 显示 HyperOS 配置检查清单。
   - 配置声音、振动、锁屏内容是否隐藏。

### 5.2 通知渠道

至少创建两个渠道：

| 渠道 ID | 重要性 | 用途 |
|---|---:|---|
| `connection_service` | 低 | 前台长连接常驻通知，静音、无振动 |
| `urgent_alerts` | 高 | 新事件通知，允许横幅、锁屏、声音和振动 |

真正的事件通知必须使用唯一通知 ID，不能一直覆盖同一条通知。通知文本开头应包含事件时间或接收时间，例如：

```text
[2026-09-25 18:42:15] Instagram Story
@example 发布了新快拍
```

Android 13 及以上必须在合适的页面上下文中请求 `POST_NOTIFICATIONS` 权限。用户拒绝后要明确显示当前不可通知，不得循环弹权限请求。

### 5.3 长连接行为

WebSocket 客户端应满足：

- 前台服务启动后建立连接。
- 每 25 秒发送一次轻量心跳，实际值可由服务端下发。
- 断线重连采用指数退避和随机抖动，例如 1、2、5、10、30、60 秒，之后最大保持 60 秒。
- 网络恢复后立即尝试重连。
- 服务端重启、网络切换和 Wi-Fi/移动网络切换不能导致永久离线。
- 收到事件后先本地持久化，再显示通知并发送 `received` ACK。
- 重复收到同一 `event_id` 时不得重复弹出通知。
- 重连成功后使用 REST 接口补拉最后确认序号之后的事件。

WorkManager 只能用于持久化补偿检查和有限重试，不能把它当成实时长连接调度器，也不能设计为每几秒执行一次。

## 6. 协议与接口契约

### 6.1 配对原则

由于 App 仅供所有者使用，采用一次性配对码即可：

1. 服务端生成短时有效的一次性配对码或二维码。
2. App 提交配对码及设备信息。
3. 服务端返回 `device_id` 和长期设备令牌。
4. 长期设备令牌保存到 Android Keystore 保护的本地存储中。
5. 服务端只保存令牌摘要，不保存明文令牌。
6. 配对码使用后立即失效。

长期令牌、服务端密钥、数据库密码均不得硬编码在 APK 中。

### 6.2 建议 REST 接口

```text
POST /api/mobile/pair
GET  /api/mobile/device
POST /api/mobile/device/revoke
GET  /api/mobile/events?after_sequence={sequence}
POST /api/mobile/events/{event_id}/received
POST /api/mobile/events/{event_id}/opened
POST /api/mobile/test-notification
GET  /api/mobile/health
```

除配对接口外，所有接口使用：

```http
Authorization: Bearer <device_token>
```

生产连接必须使用 HTTPS/WSS。开发阶段可允许局域网 HTTP/WS，但必须通过显式 Debug 构建配置开启，Release 构建不得默认允许明文流量。

### 6.3 WebSocket 地址

```text
wss://<server>/api/mobile/ws
```

认证优先使用连接时的短期票据，不建议把长期 Token 直接放入 URL 查询参数，因为 URL 容易进入代理和服务器日志。

推荐流程：

```text
App 使用长期设备 Token 调用 REST
        ↓
获取 60 秒有效的 WebSocket ticket
        ↓
使用 ticket 建立 WebSocket
```

### 6.4 统一事件格式

```json
{
  "protocol_version": 1,
  "message_type": "event",
  "event_id": "019d0000-0000-7000-8000-000000000001",
  "sequence": 1024,
  "event_type": "instagram.story.created",
  "priority": "urgent",
  "occurred_at": "2026-09-25T18:42:10+09:00",
  "created_at": "2026-09-25T18:42:12+09:00",
  "title": "Instagram Story",
  "body": "@example 发布了新快拍",
  "data": {
    "username": "example",
    "story_pk": "1234567890",
    "media_type": "video",
    "detail_url": "/api/mobile/events/019d0000-0000-7000-8000-000000000001"
  }
}
```

Android App 必须忽略无法识别的 `data` 字段，不能因为服务器增加字段而解析失败。未知 `event_type` 仍应按通用通知展示。

ACK 示例：

```json
{
  "protocol_version": 1,
  "message_type": "ack",
  "event_id": "019d0000-0000-7000-8000-000000000001",
  "status": "received",
  "client_time": "2026-09-25T18:42:13+09:00"
}
```

## 7. 服务端新增模块建议

现有 Python 项目建议新增：

```text
bot/api/routes/mobile_notifications.py
bot/services/mobile_notification_service.py
bot/services/mobile_connection_manager.py
bot/database/models/mobile_notification.py
migrations/versions/<revision>_add_mobile_notifications.py
```

建议数据库实体：

### `mobile_devices`

- `id`
- `device_name`
- `token_hash`
- `platform`
- `app_version`
- `last_seen_at`
- `last_ack_sequence`
- `is_active`
- `created_at`
- `updated_at`
- `revoked_at`

### `notification_events`

- `id`，对应 `event_id`
- `sequence`，全局单调递增且唯一
- `event_type`
- `priority`
- `title`
- `body`
- `payload_json`
- `occurred_at`
- `created_at`

### `notification_deliveries`

- `id`
- `event_id`
- `device_id`
- `sent_at`
- `received_at`
- `opened_at`
- `last_error`
- `retry_count`

数据库结构必须通过 Alembic 迁移创建，不能只依赖 `Base.metadata.create_all()` 更新已有数据库。

## 8. HyperOS 首次使用引导

App 首次配置完成后，应显示以下引导清单，但不要假装可以由代码自动完成所有设置：

1. 允许通知权限。
2. 为 `urgent_alerts` 开启锁屏通知、悬浮通知、声音和振动。
3. 将 App 的省电策略设置为“不限制”。
4. 允许自启动。
5. 在最近任务中锁定 App，降低被一键清理的概率。
6. 不要在系统设置中对 App 执行“强行停止”。
7. 确认常驻通知显示“已连接”。

App 应提供打开对应系统设置页的按钮。无法准确跳转到某个 HyperOS 私有页面时，跳转到当前 App 的系统详情页并展示文字步骤，不要依赖未经验证的私有 Intent。

## 9. 视觉与文案

App 名称固定为 `桜色男孩`，整体可以使用低饱和樱花粉作为强调色，但可读性优先，必须同时支持深色模式。

建议首页状态：

```text
桜色男孩

● 已连接
服务器：在线
最近心跳：5 秒前
最近通知：2026-09-25 18:42:15

[发送测试通知]  [连接设置]
```

错误信息必须能指导用户下一步操作。例如：

```text
无法连接服务器。将在 30 秒后重试。
请检查网络、服务器地址和设备授权状态。
```

不要只显示 `Error`、异常类名或原始堆栈。

## 10. 首期实现顺序

### 阶段 A：Android 独立原型

1. 创建 Kotlin + Compose 项目。
2. 创建两个通知渠道。
3. 完成本地测试通知。
4. 完成前台服务和常驻状态通知。
5. 用本地 Mock WebSocket 验证事件接收、去重和断线重连。

### 阶段 B：服务端接口

1. 增加移动设备、通知事件和送达记录模型。
2. 创建 Alembic 迁移。
3. 实现配对、认证、WebSocket 和补拉接口。
4. 实现服务端测试通知入口。

### 阶段 C：联调

1. Android App 与测试服务器配对。
2. 锁屏后从服务端发送单条测试事件。
3. 验证收到、展示、点击和 ACK 全链路。
4. 验证服务器重启、手机断网和 App 进程被回收后的恢复。

### 阶段 D：接入真实业务

1. 将 Instagram Story 监控产生的事件转换为统一通知事件。
2. 同时发送 Android 通知和 Telegram 备用通知。
3. 根据 Android ACK 记录实际送达延迟。

## 11. 验收标准

首期完成必须满足：

- App 安装在小米 14 后可以与服务器安全配对。
- App 前台服务运行时有一条低打扰常驻通知。
- 服务端发送事件后，锁屏状态下能出现高重要性通知。
- 通知标题和正文包含可区分的新时间或事件信息。
- 相同 `event_id` 无论重发多少次，只展示一次业务通知。
- 断网 5 分钟后恢复网络，遗漏事件能够自动补拉。
- Python 服务端重启后 App 能够自动重连。
- App 被系统回收后，在系统允许的条件下能够恢复连接。
- 手机重启后，在用户已允许自启动的条件下能够恢复服务；若无法自动恢复，App 必须明确显示修复提示。
- 服务端能够看到 `sent`、`received`、`opened` 三个阶段的时间。
- 设备令牌不会出现在普通日志、截图页面或 URL 中。
- 用户停止连接后，App 不再偷偷启动前台服务。

实时性是目标而不是绝对保证。正常联网且前台连接健康时，服务端创建事件到 Android 展示通知的目标延迟为 1～5 秒；测试报告应记录真实 P50/P95 延迟，不得只凭主观感受宣称“秒到”。

## 12. 首期明确不做

- 不接入 Mi Push、华为 Push、OPPO Push、vivo Push。
- 不把 FCM 作为首期必需依赖。
- 不发布到任何应用市场。
- 不支持陌生用户注册和多租户。
- 不在 App 内保存 Instagram 账号密码。
- 不在 App 内直接轮询 Instagram。
- 不默认使用全屏 Intent 强制覆盖锁屏。
- 不伪装电话、闹钟或媒体播放以前台常驻。
- 不追求第一版就加入复杂动态主题、社交功能或完整管理后台。

## 13. 后续扩展方向

底层事件协议稳定后，可在不改动连接层的情况下增加：

- Emby 服务状态和新增媒体通知。
- 下载完成、失败和磁盘空间告警。
- 机器人异常、数据库异常和服务器离线告警。
- 红包、审核或管理操作提醒。
- App 内远程查看任务状态。
- 经明确授权后的有限远程控制能力。
- 可选的 FCM 备用通道。

所有未来功能都通过新的 `event_type` 和独立功能模块扩展，不能继续向一个巨型通知类堆积条件分支。

## 14. 官方规则参考

- Android 13 及以上通知权限：<https://developer.android.com/develop/ui/compose/notifications/notification-permission>
- Android 前台服务类型：<https://developer.android.com/develop/background-work/services/fgs/service-types>
- Android 后台启动前台服务限制：<https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start>
- WorkManager：<https://developer.android.com/reference/androidx/work/WorkManager>

实现时必须重新核对开发当日的 Android 官方文档。Android 后台执行规则会随目标 SDK 调整，本文档描述的是架构约束，不代替最新平台规范。
