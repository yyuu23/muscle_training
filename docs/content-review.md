# 内容审核流程

对应 plan.md §10；实现：`apps/api/src/app/modules/catalog/`、`content/`。

## 内容格式

- `content/exercises/*.yaml` — 每动作一个文件（schema 见 `content/schemas/exercise.schema.json`）
- `content/templates/*.yaml` — 训练模板（`template.schema.json`）
- 策略参数：`content/policies/progression_v1.yaml`、`memory_policy_v1.yaml`

## 生命周期

```text
编写 YAML（review_status: draft）
→ 校验（cli validate-content / admin GET /admin/catalog/validate）
→ 导入草稿（cli import-content / admin POST /admin/catalog/import）
→ 管理员审核发布（admin POST /admin/catalog/{kind}/{id}/review，写审核人+时间）
→ 对用户可见（exercises/templates 列表仅返回 approved）
```

## 硬性规则

1. **导入永不自动发布**：`review_status` 只能是 `draft`，导入文件中的审核字段被忽略
2. **fixture 隔离**：`fixture: true` 内容生产环境查询自动排除；计划校验直接拒绝 fixture（`fixture_in_production`）；生产禁止 `MODEL_PROVIDER=fake` 与 `DEMO_MODE`
3. **不可变内容版本**：修改创建新 `content_version`，旧计划保留原快照；`(slug, content_version)` 唯一
4. **替代动作存在性**：`approved_alternatives` 引用的 slug 必须在目录中（validate 检查）
5. **时间估算由代码计算**：模板 `time_estimation_parameters`（每组秒数/热身/切换）驱动，不使用模型输出的预计时间
6. 无已审核模板时计划生成返回 `CONTENT_NOT_READY`

## 内容状态

| 阶段 | 入口 |
|---|---|
| 当前 | 全部合成内容（draft），fixture 测试内容两套 |
| 阶段 8 | 首批 10–20 份真实资料 + 正式模板人工审核后发布 |
