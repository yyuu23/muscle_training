# content/ 内容目录

本目录存放动作、模板与策略内容的 YAML 定义。**全部为自编合成内容，不假托任何真实作者。**

## 目录结构

```text
content/
├── schemas/           # JSON Schema（导入校验参考）
│   ├── exercise.schema.json
│   ├── template.schema.json
│   └── source.schema.json
├── exercises/         # 每个动作一个 YAML 文件
├── templates/         # 训练模板
├── policies/          # 进阶策略与记忆策略参数
└── fixtures/          # 合成测试内容（fixture=true，生产自动排除）
```

## 生命周期（plan §10.1）

1. 写入 YAML 文件（`review_status` 恒为 `draft`，导入操作不会也不允许自动发布）
2. 校验：`uv run --project apps/api python -m app.cli validate-content --content-root content --kind exercises`
3. 导入草稿：`uv run --project apps/api python -m app.cli import-content --content-root content --kind exercises`
4. 管理员审核发布：前端「内容管理」页或 `/api/v1/admin/catalog/exercises/{id}/review`（写入审核人与时间）

## 硬性规则

- `fixture: true` 的内容**永远不能进入生产环境**（生产查询自动过滤，计划校验拒绝）
- 导入文件不能自行伪造审核完成：`review_status` 只能是 `draft`
- 替代动作 `approved_alternatives` 引用的 slug 必须存在于目录
- 时间估算由代码根据模板参数计算，不使用模型输出的预计时间
- 没有任何已审核模板时，计划生成返回 `CONTENT_NOT_READY`

## 与阶段 8 的关系

首批 10-20 份**真实来源资料**与正式模板审核属于阶段 8（内容准备与试用），本目录当前提供的是完整的格式、流程与合成测试内容。
