# 私人健身教练 Agent

一个为 2-5 人小团队设计的 AI 健身教练应用，支持个性化训练计划生成、离线训练记录、知识库管理和周度复盘。

## 特性

- 📝 **个人档案管理** - 记录身体条件、训练经验、可用器械和时间约束
- 🎯 **智能计划生成** - 基于个人条件和知识库的 AI 训练计划
- 📱 **离线优先** - PWA 支持，手机离线记录训练，联网后自动同步
- 📚 **知识库** - 导入健身视频/文档，自动转写和分块索引
- 📊 **训练记录** - 详细的组数、重量、次数、RIR 记录
- 🔄 **周度复盘** - 自动生成训练总结和调整建议
- 🔐 **数据隔离** - 用户间完全隔离，邀请制注册
- 💾 **备份恢复** - 加密备份到云端和本地

## 技术栈

### 后端
- Python 3.12, FastAPI, SQLAlchemy 2, Alembic
- PostgreSQL 17 + pgvector
- 阿里云百炼 (Qwen-Plus, Paraformer, Embedding)

### 前端
- React, TypeScript, Vite
- TanStack Query, React Hook Form
- IndexedDB (Dexie.js), PWA

### 部署
- Docker Compose
- Caddy (反向代理)
- 阿里云 OSS (对象存储)

## 快速开始

### 前置要求

- Python 3.12+
- Node.js 24 LTS
- PostgreSQL 17
- pnpm 10+
- uv (Python 包管理器)

### 开发环境设置

1. **克隆仓库**
```bash
git clone https://github.com/yyuu23/muscle_training.git
cd muscle_training
```

2. **安装依赖**
```bash
# 后端依赖
cd apps/api
uv sync

# 前端依赖
cd ../web
pnpm install
```

3. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入数据库连接和 API 密钥
```

4. **启动开发环境**
```bash
# 启动 PostgreSQL 和其他服务
docker-compose -f compose.dev.yml up -d

# 运行数据库迁移
cd apps/api
uv run alembic upgrade head

# 启动后端
uv run uvicorn app.main:app --reload

# 启动前端 (新终端)
cd apps/web
pnpm dev
```

5. **访问应用**
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 项目结构

```
muscle_training/
├── apps/
│   ├── api/              # FastAPI 后端
│   │   ├── src/app/      # 应用代码
│   │   ├── migrations/   # Alembic 数据库迁移
│   │   └── tests/        # 后端测试
│   └── web/              # React 前端
│       ├── src/          # 前端代码
│       └── tests/        # 前端测试
├── contracts/            # OpenAPI 契约
├── content/              # 动作和模板内容
├── evals/                # Agent 评测用例
├── scripts/              # 构建和维护脚本
├── deploy/               # 部署配置
└── docs/                 # 文档
```

## 开发工作流

### 运行测试
```bash
# 后端测试
cd apps/api
uv run pytest

# 前端测试
cd apps/web
pnpm test

# E2E 测试
pnpm test:e2e
```

### 代码检查
```bash
# Python (Ruff)
cd apps/api
uv run ruff check .
uv run ruff format .

# TypeScript
cd apps/web
pnpm lint
```

### 数据库迁移
```bash
cd apps/api

# 创建新迁移
uv run alembic revision --autogenerate -m "描述"

# 应用迁移
uv run alembic upgrade head

# 回滚迁移
uv run alembic downgrade -1
```

## 部署

详见 [部署文档](docs/deployment.md)

## 许可

本项目为个人使用项目，暂不对外开放。

## 文档

- [架构设计](docs/architecture.md)
- [领域规则](docs/domain-rules.md)
- [数据模型](docs/data-model.md)
- [API 契约](docs/api-contract.md)
- [Agent 工作流](docs/agent-workflows.md)
- [离线同步](docs/offline-sync.md)
- [知识库导入](docs/knowledge-ingestion.md)
- [备份恢复](docs/backup-and-restore.md)

## 预算控制

目标: 100-300 元/月 (不含开发人工成本)
- 服务器: 60-120 元
- 模型 API: 20-80 元
- 存储备份: 5-20 元
- 域名: 5-10 元
- 其他: 10-30 元
