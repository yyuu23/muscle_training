# 实施进度（真实状态）

更新于：2026-11-12。对照 [plan.md](plan.md) 八阶段。状态图例：✅ 完成 ｜ 🟦 代码完成-待验证 ｜ ⬜ 未开始。

> **验证限制**：本次实施会话中 `uv`/`pnpm`/`docker`/`python` 脚本执行被环境安全策略阻止，所有测试、迁移、构建**未实际运行**。代码与测试已就绪，验证清单见 [docs/acceptance.md](docs/acceptance.md)。

## 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| 1 工程底座 | ✅ | /api/v1 前缀、统一错误体、双健康检查、CI（.github/workflows/ci.yml）、迁移完全重写（30 表） |
| 2 无 AI 记录应用 | 🟦 | auth（Cookie+CSRF+token哈希）、profiles（事实/候选/版本锁）、plans（草稿/采用/差异/校验）、workouts（统计/更正/版本冲突）、measurements、nutrition、catalog 管理（导入/校验/审核/发布）、memory、CLI 10 命令全部完成 |
| 3 离线与同步 | 🟦 | 六事件幂等 API、快照、前端 outbox/sync_engine/snapshot_cache/account_boundary 统一写入路径、全部页面改造完成；断网 E2E 未跑 |
| 4 知识入库与 RAG | 🟦 | storage(filesystem/oss)、media(FFmpeg/字幕)、providers(qwen+fake)、rag(分块/jieba/RRF/引用校验/索引切换)、knowledge 模块、jobs(队列/租约/worker/调度/6类handler) |
| 5 Agent 与计划生成 | 🟦 | orchestrator、limits（3次/6次/60s/12K/预算）、context_builder（裁剪序+不可裁项）、tools、输出三层校验+一次修复、10 个 prompt、chat/计划生成任务 |
| 6 复盘与长期调整 | 🟦 | progression（hold+double_progression_v1 九条件）、reviews（代码统计+模型解释+数据不足固定结果+stale重生成）、planning_revision 收口 |
| 7 备份恢复与部署 | 🟦 | backup（pg_dump快照/manifest/age加密/7日4周/恢复拒绝非空+账本重放+会话撤销）、exports、deletion 账本、download/verify/install 脚本 |
| 8 内容准备与试用 | ⬜ | 不在本次范围；当前 content/ 全部为合成 draft 内容（9 动作+3 模板+策略+fixtures+15 条评测种子） |

## 本次对旧实现的关键修正（对齐 plan）

| 旧实现 | 修正为 |
|---|---|
| Bearer token 存 localStorage | HttpOnly Cookie 会话 + CSRF（写请求校验），DB 只存 token 哈希 |
| axios 手写 DTO | fetch 封装（cookie 凭据/CSRF 头/请求ID/统一错误体）；契约生成命令就绪 |
| 在线直连 API + 离线本地两套写入 | 单一路径：本地 Dexie + outbox → POST /sync/events（在线离线一致） |
| API 前缀 /api | /api/v1 |
| sync_events 为幂等缓存表 | 事件账本：(user_id, event_id) 唯一 + payload_hash + 逐项独立事务 |
| 计划采用无依据校验 | basis 三元组校验，不符返回 409 PLAN_CONTEXT_STALE |
| invites/auth_sessions 明文 | 哈希存储；新增 password_reset_tokens |
| jobs 状态机/字段不符 | 7 态状态机 + dedupe_key + 租约 + run_after + external_task_id 续传 |

## 验证清单（用户执行）

```powershell
pnpm install --frozen-lockfile
uv sync --project apps/api --frozen
docker compose -f compose.dev.yml up -d db
uv run --project apps/api alembic -c apps/api/alembic.ini upgrade head
uv run --project apps/api ruff check apps/api
uv run --project apps/api pytest apps/api/tests/unit -q
# 集成测试（先建 muscle_test 库）
$env:TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/muscle_test"
uv run --project apps/api pytest apps/api/tests/integration -q
pnpm contracts:generate && pnpm lint && pnpm typecheck && pnpm test:web && pnpm build
.\scripts\dev.ps1   # 冒烟：注册→建档→生成计划→记训练
```

## 遗留事项（按优先级）

1. 运行上方验证清单并修复发现的问题（集成测试 conftest 首跑可能需微调）
2. `pnpm contracts:generate` 后将前端手写类型切换为生成的 schema.ts（消除与 plan §4.3 的偏差）
3. 补前端 Vitest/Playwright 用例（plan §12.3）
4. 启用数据库层 RLS（plan §9.3，当前应用层隔离）
5. tests/live/ 真实 API 测试（需 DASHSCOPE_API_KEY）
6. 阶段 8：真实内容准备与审核、完整 60+ 评测案例、两周试用
