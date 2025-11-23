<h1 align="center"><em>Telegram Bot Template</em></h1>

<h3 align="center">
  完整的 Telegram Bot 解决方案：Bot + API 服务器 + Web 管理界面
</h3>

<p align="center">
  <a href="https://github.com/donBarbos/telegram-bot-template/tags"><img alt="GitHub tag (latest SemVer)" src="https://img.shields.io/github/v/tag/donBarbos/telegram-bot-template"></a>
  <a href="https://github.com/donBarbos/telegram-bot-template/actions/workflows/linters.yml"><img src="https://img.shields.io/github/actions/workflow/status/donBarbos/telegram-bot-template/linters.yml?label=linters" alt="Linters Status"></a>
  <a href="https://github.com/donBarbos/telegram-bot-template/actions/workflows/docker-image.yml"><img src="https://img.shields.io/github/actions/workflow/status/donBarbos/telegram-bot-template/docker-image.yml?label=docker%20image" alt="Docker Build Status"></a>
  <a href="https://www.python.org/downloads"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
  <a href="https://github.com/donBarbos/telegram-bot-template/blob/main/LICENSE"><img src="https://img.shields.io/github/license/donbarbos/telegram-bot-template?color=blue" alt="License"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Code style"></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json" alt="Package manager"></a>
<p>

## ✨ 功能特性

### 🤖 Telegram Bot
-   [x] 基于 [`aiogram`](https://aiogram.dev/) 的异步 Telegram Bot
-   [x] 完整的用户管理和消息处理系统
-   [x] 支持群组消息保存和导出功能
-   [x] 管理员命令和权限控制
-   [x] 国际化支持 (i18n) 使用 GNU gettext 和 [`Babel`](https://pypi.org/project/Babel/)

### 🌐 Web 管理界面
-   [x] 现代化的 React + TypeScript 前端界面
-   [x] 基于 [`TanStack Table`](https://tanstack.com/table) 的数据表格
-   [x] 响应式设计，支持移动端访问
-   [x] 实时数据展示和用户管理
-   [x] 优雅的 UI 组件库集成

### 🔌 API 服务器
-   [x] 基于 [`FastAPI`](https://fastapi.tiangolo.com/) 的高性能 API 服务
-   [x] RESTful API 设计，支持 CORS
-   [x] 自动生成 API 文档 (Swagger/OpenAPI)
-   [x] 与 Telegram Bot 数据同步


### 🛠️ 开发与部署
-   [x] 无缝的 `Docker` 和 `Docker Compose` 支持
-   [x] 用户数据导出功能 (`.csv`, `.xlsx`, `.json`, `yaml`)
-   [x] 完整的 CI/CD 流水线配置
-   [x] 数据库迁移支持 [`Alembic`](https://pypi.org/project/alembic/)
-   [x] [`Pydantic V2`](https://pypi.org/project/pydantic/) 数据验证

## 🚀 快速开始

### 🐳 Docker 部署 _(推荐方式)_

1. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置必要的环境变量
   ```

2. **启动所有服务**
   ```bash
   docker compose up -d --build
   ```
   > 💡 默认 Compose 仅启动 Bot、API、Web、MySQL、备份与迁移服务。如需监控或 Redis，可在 `docker-compose.yml` 中自行扩展。

3. **访问服务**
   - **Telegram Bot**: 在 Telegram 中搜索你的 Bot
   - **Web 管理界面**: http://localhost:3000
   - **API 文档**: http://localhost:8000/docs

### 💻 本地开发

#### 📋 前置要求
- Python 3.10+
- Node.js 18+ 和 pnpm
- MySQL 数据库

#### 🔧 安装步骤

1. **克隆项目并安装 Python 依赖**
   ```bash
   git clone <repository-url>
   cd telegram-bot-template
   uv sync --frozen --all-groups
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置数据库和 Bot Token
   ```

3. **数据库迁移**
   ```bash
   uv run alembic upgrade head
   ```

4. **一键启动** _(推荐)_

   使用统一启动脚本并行启动 Bot、API 与 Web，启动后终端会打印横幅“Bot & API & Web”以及 Web 本地与局域网访问地址：

   ```bash
   uv run python run_all.py
   ```

   - Windows 用户也可以直接运行：
     ```bash
     python run_all.py
     ```
     需要确保已安装基本依赖：
     ```bash
     pip install aiogram loguru
     ```

   - 启动日志中会显示：
     - 横幅行：`🚀 项目名 | 🧩 Bot & API & Web`
     - Web 本地地址：如 `http://localhost:3000`
     - Web 局域网地址：如 `http://192.168.x.x:3000`
     - 若端口占用，Vite 可能自动切换端口，统一入口会跟随日志打印真实地址

5. **分开启动** (可选，需要三个终端窗口)

   **终端 1 - Telegram Bot**
   ```bash
   uv run python -m bot
   ```

   **终端 2 - API 服务器**
   ```bash
   uv run python run_api.py
   ```

   **终端 3 - Web 前端**
   ```bash
   cd web
   pnpm install
   pnpm dev
   ```

#### 🌐 服务访问地址

| 服务 | 地址 | 描述 |
|------|------|------|
| **Telegram Bot** | Telegram 应用 | 与用户交互的 Bot |
| **Web 管理界面** | http://localhost:3000 | React 前端管理界面 |
| **API 服务器** | http://localhost:8000 | FastAPI 后端服务 |
| **API 文档** | http://localhost:8000/docs | Swagger API 文档 |

> 提示：后端 API 路由统一挂载在 `/api` 前缀，开发模式下前端通过 Vite 代理将以 `/api` 开头的请求转发到后端，避免跨域。

#### 🔄 开发工作流

1. **修改 Bot 逻辑**: 编辑 `bot/` 目录下的文件
2. **修改 API**: 编辑 `api/` 目录下的文件  
3. **修改前端**: 编辑 `web/src/` 目录下的文件
4. **数据库变更**: 使用 `uv run alembic revision --autogenerate -m "描述"`

## 🌍 环境变量配置

所有服务（Bot、API、前端、Docker Compose）都从同一个 `.env` 文件读取配置。首次启动前先执行 `cp .env.example .env`，然后只需维护这一份文件。启动项目至少需要配置 Bot Token 和数据库，其他配置可按需开启。

### 🔑 必需配置

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `BOT_TOKEN` | Telegram Bot API Token | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `OWNER_ID` | 所有者用户 ID（唯一、必填） | `1369588230` |
| `ADMIN_IDS` | 管理员用户 ID 列表（逗号分隔） | `123456789,987654321` |
| `DB_HOST` | 数据库主机地址 | `localhost` |
| `DB_PORT` | 数据库端口 | `3306` |
| `DB_USER` | 数据库用户名 | `root` |
| `DB_PASS` | 数据库密码 | `password` |
| `DB_NAME` | 数据库名称 | `telegram_bot` |

### 🔧 API 服务器配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `API_HOST` | API 服务器主机 | `0.0.0.0` |
| `API_PORT` | API 服务器端口 | `8000` |
| `API_DEBUG` | API 调试模式 | `False` |
| `API_ALLOWED_ORIGINS` | CORS 允许的来源 | `http://localhost:3000,http://127.0.0.1:3000` |


### 🌐 Webhook 配置 (可选)

| 变量名 | 描述 |
|--------|------|
| `USE_WEBHOOK` | 是否使用 Webhook 模式 |
| `WEBHOOK_BASE_URL` | Webhook 基础 URL |
| `WEBHOOK_PATH` | Webhook 路径 |
| `WEBHOOK_SECRET` | Webhook 密钥 |
| `WEBHOOK_HOST` | Webhook 主机 |
| `WEBHOOK_PORT` | Webhook 端口 |


## 📂 项目结构

```bash
.
├── assets/ # 项目资源（横幅 banner、图片等）
├── bot/ # Telegram Bot 源代码
│   ├── __main__.py # Bot 主入口点（启动横幅、日志配置、轮询启动）
│   ├── runtime/ # 运行期钩子
│   │   └── hooks.py # 启动/关闭钩子、API 并行启动
│   ├── core/ # 核心配置和组件
│   │   ├── config.py # 全局设置（项目名、调试、数据库等）
│   │   └── loader.py # 机器人与调度器初始化
│   ├── api/ # FastAPI 服务器(独立包)
│   │   ├── app.py # API 应用主模块（路由挂载、生命周期、日志）
│   │   ├── logging.py # API 侧日志中间件
│   │   └── routes/ # API 路由定义
│   │       ├── admins.py # 管理员相关接口
│   │       ├── dashboard.py # 仪表盘统计接口
│   │       ├── users.py # 用户管理接口
│   │       └── webhooks.py # Webhook 接口
│   ├── database/ # 数据库模型和连接
│   │   ├── database.py # 异步数据库连接&Session 管理
│   │   └── models/ # SQLAlchemy 数据模型
│   │       ├── base.py # 模型基类（时间戳、ID等）
│   │       ├── config.py # 配置表
│   │       ├── audit_log.py # 审计日志
│   │       ├── group_config.py # 群组配置
│   │       ├── message.py # 消息记录
│   │       ├── statistics.py # 统计指标
│   │       ├── user.py # 用户
│   │       └── user_state.py # 用户状态
│   ├── handlers/ # 命令和交互处理器
│   │   ├── admin/ # 管理员子路由
│   │   │   └── admin_commands.py # 管理员命令
│   │   ├── group/ # 群组子路由
│   │   │   ├── group_config.py # 群组配置命令
│   │   │   ├── group_message_saver.py # 群消息保存
│   │   │   └── message_export.py # 群消息导出
│   │   ├── start.py # /start 命令
│   │   ├── menu.py # 菜单与导航
│   │   ├── info.py # 信息查询
│   │   ├── export_users.py # 用户导出
│   │   ├── support.py # 支持与反馈
│   │   └── message_export.py # 私聊消息导出
│   ├── middlewares/ # 中间件模块
│   │   ├── logging.py # Bot 侧日志
│   │   ├── throttling.py # 频率限制
│   │   ├── auth.py # 鉴权与管理员校验
│   │   ├── channel_subscribe.py # 频道订阅检查
│   │   └── database.py # DB 会话注入
│   ├── filters/ # 消息过滤器
│   │   ├── admin.py # 管理员过滤器
│   │   └── number.py # 数字过滤器
│   ├── keyboards/ # 自定义键盘
│   │   ├── default_commands.py # 默认命令键盘
│   │   ├── inline/ # 内联键盘
│   │   └── reply/ # 回复键盘
│   ├── services/ # 业务逻辑服务
│   │   ├── users.py # 用户服务
│   │   ├── group_config_service.py # 群组配置服务
│   │   ├── message_export.py # 消息导出服务
│   │   └── analytics.py # 分析服务聚合
│   ├── analytics/ # 分析服务集成（可选）
│   │   └── google/client.py # Google 集成示例
│   ├── cache/ # 缓存层（默认内存，不依赖 Redis）
│   │   ├── serialization.py # 序列化工具
│   │   └── memory_cache.py # 内存缓存封装（可扩展接入 Redis）
│   └── utils/ # 工具函数
│       ├── banner.py # 启动横幅打印
│       ├── command.py # 命令辅助
│       ├── singleton.py # 单例基类
│       └── users_export.py # 用户导出工具
│
├── web/ # React 前端应用
│   ├── src/
│   │   ├── components/ # React 组件
│   │   ├── features/ # 功能模块
│   │   ├── hooks/ # 自定义 Hooks
│   │   ├── routes/ # 路由配置
│   │   ├── stores/ # 状态管理
│   │   └── styles/ # 样式文件
│   ├── package.json # Node.js 依赖配置
│   ├── vite.config.ts # Vite 构建配置
│   └── tsconfig.json # TypeScript 配置
│
├── logs/ # 日志输出目录
├── migrations/ # Alembic 数据库迁移
│   ├── env.py # Alembic 环境配置
│   ├── script.py.mako # 迁移脚本模板
│   └── versions/ # 迁移版本文件
│
├── scripts/ # 实用脚本
├── run_api.py # API 服务器启动脚本
├── docker-compose.yml # Docker Compose 配置
├── pyproject.toml # Python 项目配置
├── uv.lock # UV 依赖锁定文件
├── run_all.py # 统一启动脚本（并行启动 Bot、API、Web）
└── README.md # 项目文档
```

## 🔧 技术栈

### 🤖 后端技术
-   **`aiogram`** — 异步 Telegram Bot API 框架
-   **`FastAPI`** — 现代、快速的 Web API 框架
-   **`SQLAlchemy V2`** — Python SQL 工具包和 ORM
-   **`aiomysql`** — 异步 MySQL 数据库客户端
-   **`Pydantic V2`** — 数据验证和设置管理
-   **`Alembic`** — SQLAlchemy 数据库迁移工具
-   **缓存装饰器** — 默认内存实现，可扩展接入 Redis
-   **`uvicorn`** — ASGI 服务器实现

### 🌐 前端技术
-   **`React 18`** — 用户界面构建库
-   **`TypeScript`** — JavaScript 的类型化超集
-   **`Vite`** — 下一代前端构建工具
-   **`TanStack Table`** — 强大的数据表格库
-   **`TanStack Router`** — 类型安全的路由库
-   **`Tailwind CSS`** — 实用优先的 CSS 框架
-   **`shadcn/ui`** — 可重用的 UI 组件库

### 🗄️ 数据库与缓存
-   **`MySQL`** — 关系型数据库管理系统

### 🛠️ 开发工具
-   **`uv`** — 现代 Python 包管理器
-   **`Docker`** — 容器化部署
-   **`pnpm`** — 快速、节省磁盘空间的包管理器
-   **`ESLint`** — JavaScript/TypeScript 代码检查工具
-   **`Prettier`** — 代码格式化工具

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=donBarbos/telegram-bot-template&type=Date)](https://star-history.com/#donBarbos/telegram-bot-template&Date)

## 👷 贡献指南

非常感谢你抽时间参与贡献！欢迎通过 Issue 反馈需求/问题，或者直接提交 Pull Request：

1. Fork 本仓库并创建功能分支  
2. 使用 `uv run ruff check` 等命令确保格式与静态检查通过  
3. 提交前同步最新 `main`，保证没有冲突  
4. 在 PR 描述中简要说明改动动机与测试方式

## 📝 许可证

项目遵循 MIT 协议，详情见 [`LICENSE`](./LICENSE.md)。

## 📢 联系方式

- GitHub: [@donBarbos](https://github.com/donBarbos)  
- Email: donbarbos@proton.me
### 🖥️ 启动与日志配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `BOOT_BANNER_LABEL` | 控制台启动横幅标签（例如显示 `Bot & API & Web`） | `Bot & API` |

### 🧩 权限配置（Bot）

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `OWNER_ID` | 所有者用户 ID（唯一、必填） | `1369588230` |
| `ADMIN_IDS` | 管理员用户 ID 列表（逗号分隔） | `123456789,987654321` |
| `SUPER_ADMIN_IDS` | 兼容旧字段（迁移期保留） | `123456789,987654321` |

> 说明：统一入口 `run_all.py` 会在启动时设置为 `Bot & API & Web`，也可根据需求在系统环境中自定义该变量。
