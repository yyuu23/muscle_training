# API 契约文档

## 概述

本文档描述 Muscle Training Agent API 的核心端点和数据契约。完整的 OpenAPI 规范可以通过以下方式生成：

```bash
cd apps/api
uv run python ../../scripts/export_openapi.py
```

生成的契约文件位于 `contracts/openapi.json`。

## 认证

所有需要认证的端点使用 Bearer Token 认证：

```
Authorization: Bearer <session_token>
```

会话令牌在登录或注册时返回，有效期 7 天。

## 核心端点

### 认证模块 (`/api/auth`)

#### POST /api/auth/register

使用邀请码注册新用户。

**请求体：**
```json
{
  "invite_code": "string",
  "username": "string",
  "display_name": "string",
  "password": "string"
}
```

**响应：** `201 Created`
```json
{
  "token": "string",
  "user": {
    "id": "uuid",
    "username": "string",
    "display_name": "string",
    "role": "member",
    "timezone": "Asia/Shanghai",
    "created_at": "2024-01-01T00:00:00Z"
  },
  "expires_at": "2024-01-08T00:00:00Z"
}
```

**错误响应：**
- `400 Bad Request` - 验证失败或邀请码无效
- `429 Too Many Requests` - 超过速率限制

#### POST /api/auth/login

用户登录。

**请求体：**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应：** `200 OK`
```json
{
  "token": "string",
  "user": { ... },
  "expires_at": "2024-01-08T00:00:00Z"
}
```

**错误响应：**
- `401 Unauthorized` - 用户名或密码错误
- `429 Too Many Requests` - 超过速率限制

#### GET /api/auth/me

获取当前用户信息。

**认证：** 必需

**响应：** `200 OK`
```json
{
  "id": "uuid",
  "username": "string",
  "display_name": "string",
  "role": "member",
  "timezone": "Asia/Shanghai",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST /api/auth/invites

创建邀请码（仅管理员）。

**认证：** 必需（管理员）

**请求体：**
```json
{
  "note": "string (optional)"
}
```

**响应：** `201 Created`
```json
{
  "id": "uuid",
  "code": "string",
  "expires_at": "2024-01-04T00:00:00Z",
  "used_at": null,
  "note": "string",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## 数据模型

### User

用户账户。

```typescript
interface User {
  id: string;              // UUID
  username: string;        // 规范化后的用户名
  display_name: string;    // 显示名称
  role: "admin" | "member";
  status: "active" | "deleted";
  timezone: string;        // IANA timezone
  created_at: string;      // ISO 8601
  updated_at: string;
}
```

### AuthSession

认证会话。

```typescript
interface AuthSession {
  id: string;
  user_id: string;
  token: string;          // 64 字符 URL-safe token
  expires_at: string;     // ISO 8601
  revoked: boolean;
  created_at: string;
}
```

### Invite

邀请码。

```typescript
interface Invite {
  id: string;
  code: string;           // 32 字符 URL-safe code
  created_by: string;     // User ID
  used_by: string | null;
  expires_at: string;     // 72 小时后过期
  used_at: string | null;
  note: string | null;
  created_at: string;
}
```

## 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "detail": "Error message description"
}
```

常见 HTTP 状态码：
- `400 Bad Request` - 请求验证失败
- `401 Unauthorized` - 认证失败或令牌无效
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `409 Conflict` - 版本冲突（乐观锁）
- `429 Too Many Requests` - 超过速率限制
- `500 Internal Server Error` - 服务器内部错误

## 速率限制

认证端点速率限制：
- 登录失败：15 分钟内最多 5 次
- 成功后窗口重置

其他 API 端点：
- 1 分钟内最多 100 次请求

## 数据契约版本

当前 API 版本：`v1`

所有端点前缀：`/api`

---

更新时间：2024-01-01
