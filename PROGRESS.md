# 实施进度（真实状态）

更新于：2026-11-13。对照 [plan.md](plan.md) 八阶段。状态图例：✅ 完成 ｜ 🟦 代码完成-待验证 ｜ ⬜ 未开始。

## 2026-11-13 后端安全层：RLS 启用 + 集成测试补齐（本轮）

- **RLS 全面启用**（plan §9.3，此前仅应用层隔离）：新迁移 `b2r3l4s5c7d8` —— 17 张 user_id 私有表 + 3 张 owner 表 ENABLE+FORCE RLS，共享读/私有写分离，worker 角色独立策略；迁移内显式 GRANT（alembic 建表不继承 bootstrap 的 DEFAULT PRIVILEGES）
- **用户上下文管线** `app/db/scope.py`：`set_config(..., is_local)` 事务级 + `after_begin` 事件重挂（服务层中途 commit 不丢作用域，连接归还池后不泄漏）；接线点：`get_current_user`、注册流程、worker 按任务属主重建作用域
- **dev 环境吃上真 RLS**：compose.dev 的 api/worker 分别改用 app_runtime / job_dispatcher 角色连接；alembic 优先 MIGRATION_DATABASE_URL
- **集成测试 15/15 文件齐**：新增 migrations（迁移完整性+RLS 策略+可逆性）、rls_isolation（A/B 互不可见、缺 ctx 全拒、WITH CHECK 拦截越权写）、connection_pool_scope、knowledge_visibility、source_withdrawal、job_lease_recovery、external_submission_unknown、user_delete、backup_restore_roundtrip（pg_dump/age 缺失自动 skip）、openapi_contract
- **fixtures 补齐 §10.4**：training 5 件（进阶正/反样本、per_implement 对比、助力器械、迟到日志）+ users 4 件（器械受限、第三方转述、临时不适、建档缺失）
- 集成 conftest：测试库自动创建、默认凭据对齐 compose（muscle_training/dev_password）、create_all 后授权、`migrated_db_url` fixture（临时库跑完整 alembic 链）

> ⚠️ 本轮代码仍未实际运行（会话权限阻止 uv/docker）；验证命令见下。



> **验证限制**：本次实施会话中 `uv`/`pnpm`/`docker`/`python` 脚本执行被环境安全策略阻止，所有测试、迁移、构建**未实际运行**。代码与测试已就绪，验证清单见 [docs/acceptance.md](docs/acceptance.md)。

## 2026-11-12 桌面端响应式 + 博客视觉移植（第二轮）

用户反馈桌面端"像居中的手机屏"（max-w-md 窄栏 + 底部导航所致）。参照用户博客 chunlongblog.cn 的《毛玻璃与粒子》配方完成：

- **氛围层**：`AmbientBackground` 组件（AppShell + 登录/注册挂载）——固定 400% 流动渐变（15s 循环）+ blur 光斑 + 16/8 个（桌面/移动）DOM 粒子（负延迟首屏即满屏；亮色=柔光尘、暗色=萤火虫；reduced-motion 全关）
- **玻璃化**：`.card` 全面毛玻璃（backdrop-blur 14px + 72% 半透明 + 双主题半透明描边）；新增 `.card-solid`（92% 实底）用于记组表单/历史详情等数据密集区保可读性
- **桌面布局（≥1024px）**：新增 `Sidebar`（毛玻璃侧栏：主导航 + 计划/知识库/复盘/饮食/管理直达 + 同步状态 + 用户卡 + 确认退出），底部导航与同步条 `lg:hidden`，内容区 `lg:pl-64` + `.page-container`（手机 28rem → 桌面 64rem → 1280px+ 72rem）
- **页面网格**：今日页双栏（主栏+340px 侧栏）、训练动作卡 2 列、历史瀑布双列、计划日卡 2 列、设置/饮食双栏、复盘 xl 双栏（统计列+图表叙述列）、聊天加宽至 48rem
- **交互**：`useTilt` 卡片 3D 微倾（±4°，lerp 平滑，仅 pointer:fine + ≥1024px + 非 reduced-motion），应用于进行中训练卡与当前计划卡
- 导航数据收敛到 `nav-items.ts`（纯数据可测，admin 项按角色过滤）
- 测试：design-tokens 断言扩展（渐变/粒子/玻璃/容器）+ nav-items 4 用例

## 2026-11-12 前端视觉重构 + 关键缺陷修复（第一轮）

对照 plan.md 的全面差距审计后完成（审计结论见下方"差距审计 2026-11-12"）。本轮改动：

**修复的关键缺陷**
- Tailwind 4 缺 `@theme` 导致 65 处 `primary-*`/`shadow-strong` 类全部失效（今日页头部曾白底白字不可见）→ 重写 `global.css`，建立完整双主题令牌体系（浅/暗跟随系统 + 设置页手动开关 + 防闪烁内联脚本）
- `.input` 未定义（12 处表单无样式）→ 与 `.input-field` 统一定义
- `animate-slide-up`/`animate-scale-in` 无 keyframes → 补全 8 组动画令牌
- PWA 图标目录为空（安装破损）→ 新增 `favicon.svg`/`icons/icon.svg`/`icon-maskable.svg`（哑铃 logo）；manifest 对齐
- `fonts.googleapis.com` @import（大陆不可达）→ 移除，改系统字体栈
- SW `runtimeCaching` 缓存 API 响应（违反 plan §4.7）→ 删除，改为 `navigateFallbackDenylist: [/^\/api\//]`
- `safe-area-bottom` 未定义（iOS 底栏被遮）→ 补全

**新增体验**
- UI 组件库 `components/ui/`：Button/Card/StatCard/Badge/Sheet/Toast/Skeleton/ProgressRing/Confetti
- 12 个页面全部重排：页面路由转场、列表 stagger 渐入、骨架屏、数字滚动、休息计时环形进度、训练完成庆祝、聊天 typing 指示、复盘页条形图
- `window.prompt`/`alert` 全部替换为 Sheet/Toast
- 全部动画遵循 `prefers-reduced-motion`；记组高频操作零延迟动效

**测试**：新增 `vitest.config.ts`（node 环境）+ 3 个测试文件（格式工具、周几/时间戳、**设计令牌回归断言**——直接守住上述"类失效"缺陷不再复发）。CI frontend job 不再因无测试文件而红。

**本轮未做（有意）**：未新增 motion/framer-motion 等依赖（动效全部 CSS 实现，避免 lockfile 变动）；未删除未用的 axios 依赖（避免 `--frozen-lockfile` 失配，待下次统一清理）。

## 差距审计 2026-11-12（对照 plan.md）

### 与 plan 一致（无需处理）
后端 13 模块结构、agent（6 文件+10 prompts）、rag/providers/media/storage/jobs/backup 全部就位；60 个 API 路径 /api/v1；契约链已生成（openapi.json + schema.ts）；Agent 限制代码级强制；sync_engine 退避/冻结/恢复齐；CLI 10 命令；CI 3 job 结构；31 表迁移；前端 12 页 + offline 全套 + 单一写入路径。

### 差距清单（按优先级）
1. ~~**RLS 未启用**（plan §9.3）~~ ✅ 2026-11-13 已启用（迁移 b2r3l4s5c7d8 + scope.py 管线），待运行验证
2. ~~**集成测试 5/15**~~ ✅ 2026-11-13 文件已齐 15/15（backup 项按环境 skip），待运行验证
3. **Playwright E2E 未写**（§12.3 的 10 场景）；Vitest 仅最小用例；CI 未跑 Chromium/WebKit
4. ~~**tests/fixtures**~~ ✅ 2026-11-13 training/users 9 件已补
5. **compose.prod 无备份服务容器**（§2.3/§9.6）：deploy/backup-entrypoint.sh 未接入；每日 03:00 备份无调度入口
6. `api/client.ts` 未切换到 openapi-fetch + generated/schema.ts（§4.3"不得手写 DTO"仍有偏差）
7. `scripts/run_eval.py` 缺失（§3）；evals 15/60 案例（§10.5，阶段 8）
8. `tests/live/` 为空（需 DASHSCOPE_API_KEY）
9. 整条验证链（迁移/测试/构建/E2E）从未实际运行——PROGRESS 顶部的验证清单仍待用户执行
10. knowledge_chunks / source_revisions 未加 RLS（v1 以 knowledge_sources 为门，迁移文件内有注释说明）



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
