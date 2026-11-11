# 开发注意事项

## 代码风格

### Python

遵循 PEP 8 规范，使用 Ruff 进行代码检查和格式化。

**命名约定：**
- 类名：`PascalCase`
- 函数/变量：`snake_case`
- 常量：`UPPER_SNAKE_CASE`
- 私有成员：`_leading_underscore`

**类型提示：**
- 所有函数参数和返回值必须有类型提示
- 使用 Python 3.12+ 的类型联合语法 (`str | None` 而不是 `Optional[str]`)

**Docstrings：**
```python
def function_name(param: str) -> bool:
    """
    Brief description of what the function does
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: Description of when this is raised
    """
    pass
```

### TypeScript/React

遵循 Airbnb 风格指南。

**命名约定：**
- 组件：`PascalCase`
- 函数/变量：`camelCase`
- 常量：`UPPER_SNAKE_CASE`
- 类型/接口：`PascalCase`

**组件结构：**
```typescript
// 导入
import { useState } from 'react';
import type { ComponentProps } from './types';

// 类型定义
interface Props {
  // ...
}

// 组件
export function ComponentName({ prop1, prop2 }: Props) {
  // Hooks
  const [state, setState] = useState();
  
  // 事件处理
  const handleEvent = () => {
    // ...
  };
  
  // 渲染
  return (
    <div>
      {/* ... */}
    </div>
  );
}
```

## 数据库

### 迁移

**创建新迁移：**
```bash
cd apps/api
uv run alembic revision --autogenerate -m "描述性消息"
```

**审查生成的迁移：**
- 检查 `upgrade()` 和 `downgrade()` 函数
- 验证索引和约束
- 确保外键正确
- 测试迁移的可逆性

**应用迁移：**
```bash
uv run alembic upgrade head
```

**回滚迁移：**
```bash
uv run alembic downgrade -1
```

### 模型约定

1. **主键：** 使用 UUID
2. **时间戳：** 使用 `DateTime(timezone=True)`，默认 `func.now()`
3. **软删除：** 使用 `status` 字段，不物理删除
4. **乐观锁：** 关键表添加 `version` 字段
5. **外键：** 明确指定 `ondelete` 行为

### 查询优化

- 使用 `select()` 而不是 `Query()`
- 使用 `joinedload()` 或 `selectinload()` 避免 N+1 查询
- 为频繁查询的字段添加索引
- 使用 `limit()` 限制大结果集

## API 设计

### 端点命名

遵循 RESTful 约定：
- `GET /resources` - 列表
- `GET /resources/{id}` - 详情
- `POST /resources` - 创建
- `PUT /resources/{id}` - 完整更新
- `PATCH /resources/{id}` - 部分更新
- `DELETE /resources/{id}` - 删除

### 响应格式

**成功响应：**
```json
{
  "data": { /* resource */ }
}
```

**列表响应：**
```json
{
  "data": [ /* resources */ ],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

**错误响应：**
```json
{
  "detail": "错误描述"
}
```

### 状态码

- `200 OK` - 成功
- `201 Created` - 创建成功
- `204 No Content` - 成功但无内容
- `400 Bad Request` - 请求验证失败
- `401 Unauthorized` - 未认证
- `403 Forbidden` - 权限不足
- `404 Not Found` - 资源不存在
- `409 Conflict` - 版本冲突
- `422 Unprocessable Entity` - 业务逻辑错误
- `429 Too Many Requests` - 速率限制
- `500 Internal Server Error` - 服务器错误

## 安全

### 密码

- 最小长度：12 字符
- 最大长度：128 字符
- 使用 Argon2id 哈希
- 不记录明文密码

### 会话

- 使用 256 位随机令牌
- HttpOnly + Secure + SameSite=Lax
- 7 天有效期
- 支持主动撤销

### 输入验证

- 所有用户输入必须验证
- 使用 Pydantic 模型
- 验证长度、格式、范围
- 防止 SQL 注入（使用参数化查询）

### API 密钥

- 绝不提交到版本控制
- 使用环境变量
- 生产环境必须更改默认值

## 测试

### 测试覆盖

目标：
- 单元测试：80%+ 覆盖率
- 关键路径：100% 覆盖率

### 测试组织

```
tests/
├── unit/           # 单元测试
│   ├── test_*.py
├── integration/    # 集成测试
│   ├── test_*.py
└── live/          # 实时 API 测试（手动运行）
    └── test_*.py
```

### 测试命名

```python
def test_function_name_scenario_expected_result():
    """Test that function_name does X when Y"""
    # Arrange
    # Act
    # Assert
```

### Fixtures

- 使用 `conftest.py` 共享 fixtures
- 保持 fixtures 简单和可重用
- 清理测试数据

## Git 工作流

### 分支策略

- `main` - 生产代码
- `develop` - 开发分支（如需要）
- `feature/*` - 功能分支
- `fix/*` - 修复分支

### 提交消息

格式：
```
类型: 简短描述（50字符内）

详细描述（可选，72字符换行）

关联 Issue: #123
```

类型：
- `feat` - 新功能
- `fix` - 修复
- `docs` - 文档
- `style` - 格式
- `refactor` - 重构
- `test` - 测试
- `chore` - 构建/工具

示例：
```
feat: 添加训练会话记录 API

实现了 POST /api/workouts/sessions 端点
支持离线记录的幂等性同步

关联 Issue: #42
```

## 性能

### 数据库

- 为外键添加索引
- 使用 `EXPLAIN ANALYZE` 分析慢查询
- 避免 N+1 查询
- 使用连接池

### API

- 使用异步处理
- 长时间运行的任务使用后台队列
- 实现分页
- 使用适当的 HTTP 缓存头

### 前端

- 代码分割和懒加载
- 图片优化
- 使用 React Query 缓存
- 避免不必要的重渲染

## 错误处理

### 后端

```python
try:
    # 操作
except SpecificError as e:
    logger.error(f"Error: {e}")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="用户友好的错误消息"
    )
```

### 前端

```typescript
try {
  await apiCall();
} catch (error) {
  if (error.status === 401) {
    // 重定向到登录
  } else {
    // 显示错误消息
    toast.error(error.message);
  }
}
```

## 日志

### 级别

- `DEBUG` - 详细调试信息
- `INFO` - 一般信息
- `WARNING` - 警告
- `ERROR` - 错误
- `CRITICAL` - 严重错误

### 内容

包含：
- 时间戳
- 请求 ID
- 用户 ID
- 操作类型
- 耗时

避免记录：
- 密码
- 会话令牌
- 敏感个人信息

## 依赖管理

### Python

使用 `uv` 管理依赖：
```bash
# 添加依赖
uv add package-name

# 更新依赖
uv sync --upgrade

# 检查过时依赖
uv pip list --outdated
```

### Node.js

使用 `pnpm`：
```bash
# 添加依赖
pnpm add package-name

# 开发依赖
pnpm add -D package-name

# 更新依赖
pnpm update
```

## 部署前检查清单

- [ ] 所有测试通过
- [ ] 代码检查通过（ruff, eslint）
- [ ] 数据库迁移测试
- [ ] 环境变量配置完整
- [ ] 密钥已更改（生产环境）
- [ ] API 密钥已配置
- [ ] OSS 存储桶已创建
- [ ] 备份脚本已测试
- [ ] 日志级别正确设置
- [ ] 性能测试通过
- [ ] 安全审计通过

---

更新时间：2024-11-11
