# Telegram Bot 管理后台

一个基于 Next.js 和 shadcn/ui 构建的现代化 Telegram Bot 管理后台系统。

## 功能特性

- 🔐 **安全认证**: 基于 JWT 的用户认证系统
- 📊 **数据仪表板**: 实时统计和数据可视化
- 👥 **用户管理**: 完整的用户 CRUD 操作
- 🛡️ **管理员管理**: 管理员权限和角色控制
- 🎨 **现代 UI**: 基于 shadcn/ui 的美观界面
- 📱 **响应式设计**: 支持桌面和移动设备
- 🌙 **主题支持**: 明暗主题切换
- 📈 **数据导出**: 支持用户数据导出功能

## 技术栈

- **前端框架**: Next.js 15
- **UI 组件库**: shadcn/ui + Tailwind CSS
- **状态管理**: React Hooks
- **表单处理**: React Hook Form + Zod
- **HTTP 客户端**: Axios
- **图标库**: Lucide React
- **类型检查**: TypeScript

## 快速开始

### 环境要求

- Node.js 18.0 或更高版本
- npm 或 yarn 包管理器
- 后端 API 服务（Flask 应用）

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd admin-web
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **配置环境变量**
   
   复制 `.env.local.example` 到 `.env.local` 并配置相应的环境变量：
   ```bash
   cp .env.local.example .env.local
   ```

   编辑 `.env.local` 文件：
   ```env
   # API 配置
   NEXT_PUBLIC_API_URL=http://localhost:5000/api
   API_URL=http://localhost:5000/api

   # NextAuth 配置
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=your-secret-key-here

   # 数据库配置（如果使用）
   DATABASE_URL=postgresql://username:password@localhost:5432/database

   # 应用配置
   NEXT_PUBLIC_APP_NAME=Telegram Bot Admin
   NEXT_PUBLIC_APP_VERSION=1.0.0
   ```

4. **启动开发服务器**
   ```bash
   npm run dev
   ```

5. **访问应用**
   
   打开浏览器访问 [http://localhost:3000](http://localhost:3000)

## 项目结构

```
admin-web/
├── src/
│   ├── app/                    # Next.js App Router 页面
│   │   ├── dashboard/          # 仪表板页面
│   │   ├── users/              # 用户管理页面
│   │   ├── admins/             # 管理员管理页面
│   │   ├── login/              # 登录页面
│   │   ├── layout.tsx          # 根布局
│   │   └── page.tsx            # 首页
│   ├── components/             # 可复用组件
│   │   ├── ui/                 # shadcn/ui 组件
│   │   ├── app-layout.tsx      # 应用布局组件
│   │   ├── app-sidebar.tsx     # 侧边栏组件
│   │   └── app-header.tsx      # 头部组件
│   ├── lib/                    # 工具库
│   │   ├── api.ts              # API 客户端
│   │   ├── types/              # TypeScript 类型定义
│   │   └── utils.ts            # 工具函数
│   └── styles/                 # 样式文件
├── docs/                       # 文档
│   └── API.md                  # API 接口文档
├── public/                     # 静态资源
├── .env.local                  # 环境变量配置
├── package.json                # 项目依赖
├── tailwind.config.js          # Tailwind CSS 配置
├── tsconfig.json               # TypeScript 配置
└── next.config.js              # Next.js 配置
```

## 开发指南

### 添加新页面

1. 在 `src/app/` 目录下创建新的页面文件夹
2. 创建 `page.tsx` 文件作为页面组件
3. 在侧边栏导航中添加对应的菜单项

### 添加新组件

1. 在 `src/components/` 目录下创建组件文件
2. 使用 TypeScript 定义组件的 props 类型
3. 遵循项目的命名规范和代码风格

### API 集成

使用 `src/lib/api.ts` 中的 `ApiClient` 类进行 API 调用：

```typescript
import { apiClient } from '@/lib/api';

// 获取用户列表
const users = await apiClient.getUsers(1, 10);

// 创建新用户
const newUser = await apiClient.createUser({
  email: 'user@example.com',
  password: 'password'
});
```

### 表单处理

使用 React Hook Form 和 Zod 进行表单验证：

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email('邮箱格式不正确'),
  password: z.string().min(6, '密码至少6位')
});

const form = useForm({
  resolver: zodResolver(schema)
});
```

## 部署

### 开发环境部署

1. 确保后端 API 服务正在运行
2. 配置正确的环境变量
3. 运行 `npm run dev` 启动开发服务器

### 生产环境部署

1. **构建应用**
   ```bash
   npm run build
   ```

2. **启动生产服务器**
   ```bash
   npm start
   ```

3. **使用 PM2 管理进程**
   ```bash
   # 安装 PM2
   npm install -g pm2

   # 启动应用
   pm2 start npm --name "admin-web" -- start

   # 查看状态
   pm2 status

   # 查看日志
   pm2 logs admin-web
   ```

### Docker 部署

1. **构建 Docker 镜像**
   ```bash
   docker build -t telegram-bot-admin .
   ```

2. **运行容器**
   ```bash
   docker run -p 3000:3000 \
     -e NEXT_PUBLIC_API_URL=http://your-api-url \
     -e NEXTAUTH_SECRET=your-secret \
     telegram-bot-admin
   ```

### Nginx 反向代理

配置 Nginx 反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|---------|
| `NEXT_PUBLIC_API_URL` | 前端 API 基础 URL | - | ✅ |
| `API_URL` | 服务端 API 基础 URL | - | ✅ |
| `NEXTAUTH_URL` | NextAuth 回调 URL | - | ✅ |
| `NEXTAUTH_SECRET` | NextAuth 密钥 | - | ✅ |
| `DATABASE_URL` | 数据库连接字符串 | - | ❌ |
| `NEXT_PUBLIC_APP_NAME` | 应用名称 | Telegram Bot Admin | ❌ |
| `NEXT_PUBLIC_APP_VERSION` | 应用版本 | 1.0.0 | ❌ |

### Tailwind CSS 配置

项目使用自定义的 Tailwind CSS 配置，支持：
- 自定义颜色主题
- 响应式断点
- 动画效果
- 字体配置

### TypeScript 配置

项目启用了严格的 TypeScript 检查，包括：
- 严格的空值检查
- 未使用变量检查
- 隐式 any 类型检查

## 故障排除

### 常见问题

1. **启动时出现 DLL 错误**
   
   这是 Windows 上 Next.js SWC 编译器的已知问题，不影响应用运行。如果需要解决，可以：
   ```bash
   # 使用 Babel 编译器
   npm install --save-dev @babel/core @babel/preset-env @babel/preset-react
   ```

2. **API 请求失败**
   
   检查：
   - 后端 API 服务是否正在运行
   - 环境变量配置是否正确
   - 网络连接是否正常

3. **样式不生效**
   
   确保：
   - Tailwind CSS 配置正确
   - 组件正确导入了样式
   - 没有 CSS 冲突

4. **认证问题**
   
   检查：
   - JWT token 是否有效
   - 认证配置是否正确
   - 用户权限是否足够

### 调试技巧

1. **开启详细日志**
   ```bash
   DEBUG=* npm run dev
   ```

2. **检查网络请求**
   
   使用浏览器开发者工具的网络面板查看 API 请求和响应

3. **TypeScript 类型检查**
   ```bash
   npm run type-check
   ```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范

- 使用 TypeScript 进行类型检查
- 遵循 ESLint 和 Prettier 配置
- 编写有意义的提交信息
- 添加必要的注释和文档

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 支持

如果您遇到问题或有建议，请：

1. 查看 [常见问题](#故障排除) 部分
2. 搜索现有的 [Issues](../../issues)
3. 创建新的 Issue 描述问题
4. 联系项目维护者

## 更新日志

### v1.0.0 (2024-01-01)
- 🎉 初始版本发布
- ✨ 实现用户和管理员管理功能
- 🔐 添加 JWT 认证系统
- 📊 创建数据仪表板
- 🎨 集成 shadcn/ui 组件库
- 📱 实现响应式设计
