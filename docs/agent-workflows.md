# Agent 工作流

对应 plan.md §4.4 / §7；实现：`apps/api/src/app/agent/`。

## 受控工作流（无自由多 Agent 讨论）

明确业务入口直达对应流程（不走意图分类）：
- 点击「生成计划」→ `plan_generate` 后台任务（1 次生成 + ≤1 次修复，180 秒预算）
- 点击「生成周复盘」→ `weekly_review`（统计由代码计算，模型只解释）
- 填写记组表单 → 直接业务保存（不经过模型）

自由聊天才做意图分类（`classify_intent.md`，8 类意图）。

## 交互预算（plan §7.1）

| 项 | 限制 |
|---|---|
| 模型调用 | ≤3 次（分类+生成+修复） |
| 只读工具 | ≤6 次（`agent/tools.py`，身份后端注入） |
| 总时间 | 60 秒 |
| 输入上下文 | ~12K token |
| 后台计划任务 | 1+1 次模型，180 秒 |

预算在 `agent/limits.py`（BudgetTracker）+ `model_runs` 表（重启不重置）。重试计入预算；调用前预留费用、返回后按实际结算；月预算 80% 提醒、100% 暂停新生成（查看/记录/同步/导出不受影响）。

## 上下文构建（`context_builder.py`）

裁剪顺序：无关聊天 → 低排名知识片段 → 无关原始记录 → 保留统计与最新事实。
**永不裁剪**：已确认限制、任务相关不适、器械时间约束、当前计划及依据版本。必要内容超预算 → 可解释错误（不静默丢约束）。

## 输出三层校验（`output_validation.py`）

1. Pydantic 结构（模型 schema 全部 `extra="forbid"`；Qwen JSON Object 模式不保证 schema）
2. 引用校验（引用必须属于本次检索结果、来源可访问、版本有效）
3. 领域业务校验（动作/模板已审核、器械匹配、范围限制等，`plans/validators.py`）

失败触发**一次**修复（`repair_output.md`：只修报告的错误，不改任务范围）；仍失败 → `MODEL_OUTPUT_INVALID`，不向用户展示半成品。

## 十个 Prompt（`agent/prompts/`）

system / classify_intent / answer_question / generate_plan / adjust_plan / parse_workout / extract_memory / weekly_review / extract_knowledge / repair_output。每个含 7 节：任务目标、输入字段、输出类型、缺失信息处理、不允许的行为、引用格式、事实/建议/推断区分。内容哈希版本号记录到 `model_runs.prompt_version`。

## 关键不变量

- 模型不能直接采用计划或写入实际训练；`proposed_actions` 仅四种类型且引用后端生成的合法实体 ID
- 无适用模板 → `CONTENT_NOT_READY`；档案不足 → `INSUFFICIENT_PROFILE` 并列出缺失字段
- 未知负荷 `initial_load_kg=null` + 校准说明，禁止按身高体重推算
- 第三方转述/模型推断 → 记忆候选，用户确认后才成为事实
