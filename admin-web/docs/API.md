# API 接口文档

## 概述

本文档描述了 Telegram Bot 管理后台的 API 接口规范。所有 API 接口都基于 RESTful 设计原则，使用 JSON 格式进行数据交换。

## 基础信息

- **基础 URL**: `http://localhost:5000/api` (开发环境)
- **认证方式**: Bearer Token
- **内容类型**: `application/json`
- **字符编码**: UTF-8

## 认证

### 登录

获取访问令牌以进行后续 API 调用。

**请求**
```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "password"
}
```

**响应**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "id": "1",
      "email": "admin@example.com",
      "roles": ["admin"],
      "active": true
    }
  }
}
```

### 登出

注销当前用户会话。

**请求**
```http
POST /auth/logout
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

### 获取当前用户信息

**请求**
```http
GET /auth/me
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "success": true,
  "data": {
    "id": "1",
    "email": "admin@example.com",
    "roles": ["admin"],
    "active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T12:00:00Z"
  }
}
```

## 仪表板

### 获取统计数据

获取仪表板显示的统计信息。

**请求**
```http
GET /dashboard/stats
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "success": true,
  "data": {
    "totalUsers": 1250,
    "activeUsers": 890,
    "newUsers": 45,
    "totalOrders": 3420
  }
}
```

## 用户管理

### 获取用户列表

获取分页的用户列表。

**请求**
```http
GET /users?page=1&per_page=10&search=john
Authorization: Bearer {access_token}
```

**查询参数**
- `page` (可选): 页码，默认为 1
- `per_page` (可选): 每页数量，默认为 10，最大 100
- `search` (可选): 搜索关键词，支持邮箱和用户名搜索

**响应**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "user_123",
        "email": "user@example.com",
        "active": true,
        "created_at": "2024-01-01T00:00:00Z",
        "last_login_at": "2024-01-01T12:00:00Z"
      }
    ],
    "page": 1,
    "per_page": 10,
    "total": 1250,
    "pages": 125
  }
}
```

### 获取单个用户

**请求**
```http
GET /users/{user_id}
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "success": true,
  "data": {
    "id": "user_123",
    "email": "user@example.com",
    "active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T12:00:00Z"
  }
}
```

### 创建用户

**请求**
```http
POST /users
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "securepassword",
  "active": true
}
```

**响应**
```json
{
  "success": true,
  "data": {
    "id": "user_124",
    "email": "newuser@example.com",
    "active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 更新用户

**请求**
```http
PUT /users/{user_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "email": "updated@example.com",
  "active": false
}
```

**响应**
```json
{
  "success": true,
  "data": {
    "id": "user_123",
    "email": "updated@example.com",
    "active": false,
    "updated_at": "2024-01-01T12:00:00Z"
  }
}
```

### 删除用户

**请求**
```http
DELETE /users/{user_id}
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

### 导出用户数据

导出用户数据为 CSV 格式。

**请求**
```http
GET /users/export
Authorization: Bearer {access_token}
```

**响应**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="users_export_2024-01-01.csv"`

## 管理员管理

### 获取管理员列表

**请求**
```http
GET /admins?page=1&per_page=10&search=admin
Authorization: Bearer {access_token}
```

**响应**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "admin_1",
        "email": "admin@example.com",
        "roles": ["admin"],
        "active": true,
        "created_at": "2024-01-01T00:00:00Z",
        "last_login_at": "2024-01-01T12:00:00Z"
      }
    ],
    "page": 1,
    "per_page": 10,
    "total": 5,
    "pages": 1
  }
}
```

### 创建管理员

**请求**
```http
POST /admins
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "email": "newadmin@example.com",
  "password": "securepassword",
  "active": true
}
```

**响应**
```json
{
  "success": true,
  "data": {
    "id": "admin_2",
    "email": "newadmin@example.com",
    "roles": ["admin"],
    "active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 更新管理员

**请求**
```http
PUT /admins/{admin_id}
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "email": "updated@example.com",
  "active": false
}
```

### 删除管理员

**请求**
```http
DELETE /admins/{admin_id}
Authorization: Bearer {access_token}
```

## 错误处理

### 错误响应格式

所有错误响应都遵循以下格式：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数验证失败",
    "details": {
      "email": ["邮箱格式不正确"]
    }
  }
}
```

### 常见错误代码

| 状态码 | 错误代码 | 描述 |
|--------|----------|------|
| 400 | VALIDATION_ERROR | 请求参数验证失败 |
| 401 | UNAUTHORIZED | 未授权访问 |
| 403 | FORBIDDEN | 权限不足 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突（如邮箱已存在） |
| 429 | RATE_LIMIT_EXCEEDED | 请求频率超限 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |

### 认证错误

**401 Unauthorized**
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "访问令牌无效或已过期"
  }
}
```

**403 Forbidden**
```json
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "权限不足，无法访问此资源"
  }
}
```

## 请求限制

- **频率限制**: 每个 IP 地址每分钟最多 100 次请求
- **数据大小**: 请求体最大 10MB
- **超时时间**: 30 秒

## 版本控制

API 版本通过 URL 路径进行控制：
- 当前版本: `/api/v1/`
- 向后兼容: 支持最近 2 个主要版本

## 示例代码

### JavaScript (Axios)

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// 添加请求拦截器
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 登录
const login = async (email, password) => {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
};

// 获取用户列表
const getUsers = async (page = 1, perPage = 10) => {
  const response = await api.get(`/users?page=${page}&per_page=${perPage}`);
  return response.data;
};
```

### Python (Requests)

```python
import requests

class AdminAPI:
    def __init__(self, base_url="http://localhost:5000/api"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def login(self, email, password):
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            token = data['data']['access_token']
            self.session.headers.update({'Authorization': f'Bearer {token}'})
            return data
        else:
            response.raise_for_status()
    
    def get_users(self, page=1, per_page=10):
        response = self.session.get(
            f"{self.base_url}/users",
            params={"page": page, "per_page": per_page}
        )
        return response.json()
```

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持用户和管理员管理
- 实现基础认证功能
- 添加仪表板统计接口