# 数据模型

对应 plan.md §5；实现：`apps/api/src/app/db/models/` + 迁移 `20261112_0900_a1c2d3e4f5b6_initial_schema.py`。共 30 张表。

## 全局约定

UUIDv4 主键；`TIMESTAMPTZ`；区分用户观察时间与服务器时间；NUMERIC + 十进制字符串传输；可修改记录带 `version`（修改提交 `expected_version`）；私有实体全部带 `user_id`/`owner_user_id`；Pydantic `extra="forbid"`。

## 分组

**认证（auth.py）**：`users`（role=admin/member；status=active/disabled/deleting）、`auth_sessions`（token_hash 唯一 + csrf_token，只存哈希）、`invites`（code_hash，72h 一次性）、`password_reset_tokens`、`auth_attempts`（账号/IP 哈希限速）。

**档案与记忆（profile.py）**：`profiles`（目标/经验月数/每周次数/单次分钟/可用星期/器械/重量增量，版本乐观锁）、`profile_facts`（已确认事实唯一事实源：kind×fact_key×user 唯一，provenance 四类，superseded_by 替代链）、`memory_candidates`（pending→accepted/rejected/superseded）、`user_state`（planning_revision + active_plan_id）。

**目录（catalog.py）**：`exercises`/`training_templates`（(slug, content_version) 唯一，不可变版本，review_status=draft/approved/rejected，fixture 标志）、`plan_versions`（(user_id, sequence_number) 唯一；**部分唯一索引保证每用户最多一个 active**；content JSONB=PlanContent；basis 三元组：profile_version + planning_revision + active_plan_id）。

**训练（training.py）**：`workout_sessions`（precheck/notes/version）、`session_exercises`（position/completion_status=not_recorded/partial/completed/skipped）、`workout_sets`（(session_exercise_id, set_index) 唯一；load_mode 五类；未知值 null；skipped 不伪造 0 次）、`record_revisions`（在线更正审计：previous_version/previous_value/changed_fields/reason）。

**测量与饮食（nutrition.py）**：`measurements`（weight 一等公民）、`meal_logs`（nutrition_source 四类区分用户标注与模型估计）。

**知识（knowledge.py）**：`knowledge_sources`（visibility=private 默认；status 状态机；active_revision_id）、`source_revisions`（(source_id, revision) 唯一；content_payload 存待索引内容；审核人/时间）、`knowledge_chunks`（毫秒时间戳、original/corrected 分离、TSVECTOR + pgvector HNSW 余弦索引、embedding_model+dimensions 版本化）、`assets`（object_key 寻址，retention_class=durable/temporary_import/export，status + expires_at）。

**运行数据（operations.py）**：`conversations`/`messages`（evidence_refs，90 天保留）、`weekly_reviews`（data_revision + data_cutoff_at + stale）、`jobs`（状态机 7 态、dedupe_key 唯一、lease_owner/expires_at、run_after 重调度、external_task_id 断点续传）、`sync_events`（(user_id, event_id) 唯一 + payload_hash + result 账本）、`model_runs`（预算与审计：tokens/estimated_cost(分)/latency/prompt_version/status）、`audit_events`、`backup_runs`、`deletion_ledger`。

## planning_revision 递增点（plan §5.9）

训练相关档案修改、已确认限制/偏好变化、身体观测更新、训练记录增改删、生效计划变化。普通聊天与备份下载**不**递增。（`services/planning.py` 统一实现，各 service 调用。）

## 已知差距

- 数据库层 RLS 策略未在迁移中启用（plan §9.3）；当前隔离靠应用层 user_id 过滤 + 集成测试覆盖，见 docs/acceptance.md。
- 部分角色分离 DSN（MIGRATION/JOB/BACKUP_DATABASE_URL）已在配置中预留，compose 角色脚本见 `deploy/postgres/bootstrap_roles.sql`。
