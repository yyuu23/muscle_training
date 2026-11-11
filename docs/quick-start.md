# 快速开始指南

## 前置条件

- Python 3.12+
- Node.js 22+
- PostgreSQL 17
- Docker & Docker Compose
- pnpm 10+
- uv (Python 包管理器)

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/yyuu23/muscle_training.git
cd muscle_training
```

### 2. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置以下必需项：
# - DATABASE_URL
# - SECRET_KEY (生产环境必须更改)
# - DASHSCOPE_API_KEY (如果启用 AI 功能)
```

### 3. 安装依赖

**后端：**
```bash
cd apps/api
uv sync
```

**前端：**
```bash
cd apps/web
pnpm install
```

### 4. 启动开发环境

**使用 Docker Compose：**
```bash
# 启动 PostgreSQL 和相关服务
docker-compose -f compose.dev.yml up -d

# 查看日志
docker-compose -f compose.dev.yml logs -f
```

**不使用 Docker（需要本地 PostgreSQL）：**
```bash
# 确保 PostgreSQL 17 已安装并运行
# 创建数据库
createdb muscle_training_dev

# 运行迁移（需要先实现迁移脚本）
cd apps/api
uv run alembic upgrade head
```

### 5. 启动应用

**后端：**
```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

**前端：**
```bash
cd apps/web
pnpm dev
```

### 6. 访问应用

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs (仅开发环境)

## 初始化数据

### 创建管理员账户

目前需要通过数据库直接插入第一个管理员用户和邀请码。后续版本会提供 CLI 工具。

```sql
-- 连接到数据库
psql muscle_training_dev

-- 插入管理员用户（密码哈希需要通过 Python 生成）
-- Python 生成密码哈希：
-- >>> from app.utils.password import hash_password
-- >>> hash_password("your_secure_password")
```

## 开发工作流

### 运行测试

```bash
# 启动测试数据库
docker-compose -f compose.test.yml up -d

# 运行后端测试
cd apps/api
uv run pytest

# 运行前端测试
cd apps/web
pnpm test
```

### 代码检查

```bash
# Python 代码检查
cd apps/api
uv run ruff check .
uv run ruff format .

# TypeScript 检查
cd apps/web
pnpm lint
pnpm typecheck
```

### 生成 API 类型

```bash
# 导出 OpenAPI schema
python scripts/export_openapi.py

# 生成前端类型
cd apps/web
pnpm generate:types
```

## 常见问题

### Q: 无法连接到数据库

**A:** 检查以下几点：
1. PostgreSQL 服务是否运行
2. `.env` 中的 `DATABASE_URL` 是否正确
3. 数据库是否已创建
4. pgvector 扩展是否已安装

### Q: 导入错误

**A:** 确保已经安装所有依赖：
```bash
cd apps/api && uv sync
cd apps/web && pnpm install
```

### Q: 端口被占用

**A:** 更改端口配置：
- API: 修改 `.env` 中的 `API_PORT`
- 前端: 修改 `apps/web/vite.config.ts` 中的 `server.port`

### Q: Docker 容器启动失败

**A:** 查看日志排查问题：
```bash
docker-compose -f compose.dev.yml logs
```

## 下一步

- 阅读 [架构文档](docs/architecture.md)
- 查看 [API 契约](docs/api-contract.md)
- 了解 [领域规则](docs/domain-rules.md)
- 浏览项目结构和代码

## 获取帮助

- 查看项目 README
- 阅读文档目录下的详细文档
- 查看代码中的注释和 docstring

---

更新时间：2024-11-11
