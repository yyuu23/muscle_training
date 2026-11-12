# 私人健身教练应用

供本人与少量朋友（2–5 人）使用的私人健身教练应用：建档、生成训练计划、离线记录训练、周复盘、知识库问答。完整规格见 [plan.md](plan.md)。

## 功能边界（第一版不做）

动作视频自动纠错、实时摄像头指导、医学诊断、食物照片热量识别、可穿戴设备、小程序/原生 App、支付、本地云端双向同步、模型微调、Redis/Celery/独立向量库/K8s、短信邮件推送。

## 技术栈

Python 3.12 (FastAPI + SQLAlchemy 2 + Alembic) · PostgreSQL 17 + pgvector · React 18 + TypeScript + Vite + Dexie · Qwen（百炼，可选，无密钥时记录功能完全可用）· Docker Compose · age 加密备份

## 快速开始

```powershell
Set-Location D:\py\muscle_training
Copy-Item .env.example .env          # 按需修改数据库连接

# 1. 安装依赖
pnpm install --frozen-lockfile
uv sync --project apps/api --frozen

# 2. 启动数据库（pgvector/pg17）
docker compose -f compose.dev.yml up -d db

# 3. 数据库迁移（显式步骤，不随启动自动执行）
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head

# 4. 创建管理员（密码交互输入）并生成首个邀请码
uv run --project apps/api python -m app.cli create-admin --username owner

# 5. 一键启动（API + Worker + 前端）或分别启动：
.\scripts\dev.ps1
#   uv run --project apps/api uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
#   uv run --project apps/api python -m app.jobs.worker
#   pnpm --filter @fitness/web dev
```

- 前端：http://localhost:5173 （用邀请码注册）
- API 文档：http://127.0.0.1:8000/docs

## 常用命令

```powershell
pnpm contracts:generate    # 导出 OpenAPI 契约 + 生成前端类型
pnpm contracts:check       # 校验契约是否过期
pnpm lint / typecheck      # 前端检查
pnpm test:web              # 前端单元测试
pnpm test:e2e              # Playwright
uv run --project apps/api ruff check apps/api
uv run --project apps/api pytest apps/api/tests/unit
uv run --project apps/api pytest apps/api/tests/integration   # 需 TEST_DATABASE_URL
```

CLI（`python -m app.cli --help`）：`create-admin / create-invite / create-password-reset / import-content / validate-content / export-openapi / backup / verify-backup / restore / check-production-config`

## 文档

- [docs/architecture.md](docs/architecture.md) · [docs/domain-rules.md](docs/domain-rules.md) · [docs/api-contract.md](docs/api-contract.md)
- [docs/offline-sync.md](docs/offline-sync.md) · [docs/agent-workflows.md](docs/agent-workflows.md) · [docs/knowledge-ingestion.md](docs/knowledge-ingestion.md)
- [docs/content-review.md](docs/content-review.md) · [docs/backup-and-restore.md](docs/backup-and-restore.md) · [docs/privacy-and-retention.md](docs/privacy-and-retention.md)
- [docs/acceptance.md](docs/acceptance.md) — 验收状态逐项标注
- [AGENTS.md](AGENTS.md) — 后续 AI 必须遵守的规则

## 部署与恢复

生产部署（Caddy + API + Worker + PostgreSQL + 备份）见 [docs/deployment.md](docs/deployment.md) 与 [compose.prod.yml](compose.prod.yml)。备份恢复流程见 [docs/backup-and-restore.md](docs/backup-and-restore.md)；恢复工具默认拒绝非空目标数据库。

当前实施状态见 [PROGRESS.md](PROGRESS.md)。
