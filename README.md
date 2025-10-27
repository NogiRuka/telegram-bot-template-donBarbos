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

### 📊 数据分析与监控
-   [x] 产品分析系统：支持 [`PostHog`](https://posthog.com/) 或 [`Google Analytics`](https://analytics.google.com)
-   [x] 性能监控系统：使用 [`Prometheus`](https://prometheus.io/) 和 [`Grafana`](https://grafana.com/)
-   [x] 错误追踪系统：使用 [`Sentry`](https://sentry.io/)

### 🛠️ 开发与部署
-   [x] 无缝的 `Docker` 和 `Docker Compose` 支持
-   [x] 用户数据导出功能 (`.csv`, `.xlsx`, `.json`, `yaml`)
-   [x] 完整的 CI/CD 流水线配置
-   [x] 数据库迁移支持 [`Alembic`](https://pypi.org/project/alembic/)
-   [x] Redis 缓存装饰器支持
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

3. **访问服务**
   - **Telegram Bot**: 在 Telegram 中搜索你的 Bot
   - **Web 管理界面**: http://localhost:3000
   - **API 文档**: http://localhost:8000/docs

### 💻 本地开发

#### 📋 前置要求
- Python 3.10+
- Node.js 18+ 和 pnpm
- MySQL 数据库
- Redis 服务

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
   # 编辑 .env 文件，配置数据库、Redis 和 Bot Token
   ```

3. **数据库迁移**
   ```bash
   uv run alembic upgrade head
   ```

4. **启动服务** (需要三个终端窗口)

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

#### 🔄 开发工作流

1. **修改 Bot 逻辑**: 编辑 `bot/` 目录下的文件
2. **修改 API**: 编辑 `bot/api_server/` 目录下的文件  
3. **修改前端**: 编辑 `web/src/` 目录下的文件
4. **数据库变更**: 使用 `uv run alembic revision --autogenerate -m "描述"`

## 🌍 环境变量配置

启动项目只需要配置 Bot Token、数据库和 Redis 设置，其他配置可选。

### 🔑 必需配置

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `BOT_TOKEN` | Telegram Bot API Token | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `SUPER_ADMIN_IDS` | 超级管理员用户 ID 列表 | `123456789,987654321` |
| `DB_HOST` | 数据库主机地址 | `localhost` |
| `DB_PORT` | 数据库端口 | `3306` |
| `DB_USER` | 数据库用户名 | `root` |
| `DB_PASS` | 数据库密码 | `password` |
| `DB_NAME` | 数据库名称 | `telegram_bot` |
| `REDIS_HOST` | Redis 主机地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `6379` |

### 🔧 API 服务器配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `API_HOST` | API 服务器主机 | `0.0.0.0` |
| `API_PORT` | API 服务器端口 | `8000` |
| `API_DEBUG` | API 调试模式 | `True` |
| `API_ALLOWED_ORIGINS` | CORS 允许的来源 | `http://localhost:3000` |

### 🌐 Webhook 配置 (可选)

| 变量名 | 描述 |
|--------|------|
| `USE_WEBHOOK` | 是否使用 Webhook 模式 |
| `WEBHOOK_BASE_URL` | Webhook 基础 URL |
| `WEBHOOK_PATH` | Webhook 路径 |
| `WEBHOOK_SECRET` | Webhook 密钥 |
| `WEBHOOK_HOST` | Webhook 主机 |
| `WEBHOOK_PORT` | Webhook 端口 |

### 📊 监控与分析 (可选)

| 变量名 | 描述 |
|--------|------|
| `SENTRY_DSN` | Sentry 错误追踪 DSN |
| `POSTHOG_API_KEY` | PostHog 分析 API 密钥 |
| `PROMETHEUS_PORT` | Prometheus 监控端口 |
| `GRAFANA_PORT` | Grafana 可视化端口 |
| `GRAFANA_ADMIN_USER` | Grafana 管理员用户名 |
| `GRAFANA_ADMIN_PASSWORD` | Grafana 管理员密码 |

## 📂 项目结构

```bash
.
├── bot/ # Telegram Bot 源代码
│   ├── __main__.py # Bot 主入口点
│   ├── api_server/ # FastAPI 服务器
│   │   ├── app.py # API 应用主模块
│   │   ├── config.py # API 服务器配置
│   │   └── routes/ # API 路由定义
│   ├── analytics/ # 分析服务集成 (PostHog, Google Analytics)
│   ├── cache/ # Redis 缓存逻辑
│   ├── core/ # 核心配置和组件
│   ├── database/ # 数据库模型和连接
│   │   └── models/ # SQLAlchemy 数据模型
│   ├── filters/ # 消息过滤器
│   ├── handlers/ # 命令和交互处理器
│   ├── keyboards/ # 自定义键盘
│   │   ├── inline/ # 内联键盘
│   │   └── reply/ # 回复键盘
│   ├── middlewares/ # 中间件模块
│   ├── services/ # 业务逻辑服务
│   └── utils/ # 工具函数
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
├── migrations/ # Alembic 数据库迁移
│   ├── env.py # Alembic 环境配置
│   ├── script.py.mako # 迁移脚本模板
│   └── versions/ # 迁移版本文件
│
├── configs/ # 监控配置 (Prometheus, Grafana)
│   ├── grafana/ # Grafana 配置文件
│   └── prometheus/ # Prometheus 配置文件
│
├── scripts/ # 实用脚本
├── run_api.py # API 服务器启动脚本
├── docker-compose.yml # Docker Compose 配置
├── pyproject.toml # Python 项目配置
├── uv.lock # UV 依赖锁定文件
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
-   **`Redis`** — 内存数据结构存储，用作缓存和 FSM
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
-   **`Redis`** — 内存数据库，用于缓存和会话存储

### 📊 监控与分析
-   **`Prometheus`** — 时间序列数据库，用于收集系统指标
-   **`Grafana`** — 数据可视化和分析平台
-   **`Sentry`** — 错误追踪和性能监控
-   **`PostHog`** — 产品分析平台

### 🛠️ 开发工具
-   **`uv`** — 现代 Python 包管理器
-   **`Docker`** — 容器化部署
-   **`pnpm`** — 快速、节省磁盘空间的包管理器
-   **`ESLint`** — JavaScript/TypeScript 代码检查工具
-   **`Prettier`** — 代码格式化工具

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=donBarbos/telegram-bot-template&type=Date)](https://star-history.com/#donBarbos/telegram-bot-template&Date)

## 👷 Contributing

First off, thanks for taking the time to contribute! Contributions are what makes the open-source community such an amazing place to learn, inspire, and create. Any contributions you make will benefit everybody else and are greatly appreciated.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement". Don't forget to give the project a star! Thanks again!

1. `Fork` this repository
2. Create a `branch`
3. `Commit` your changes
4. `Push` your `commits` to the `branch`
5. Submit a `pull request`

## 📝 License

Distributed under the MIT license. See [`LICENSE`](./LICENSE.md) for more information.

## 📢 Contact

[donbarbos](https://github.com/donBarbos): donbarbos@proton.me
