# 评测评分说明

## 案例格式

每条 JSONL 案例包含 `case_id / task_type / input / profile_fixture / history_fixture / knowledge_fixture / expected_evidence_ids / required_behaviors / forbidden_behaviors / scoring_notes`。**允许多种正确表述**——评的是行为约束，不是唯一参考答案。

## 评分维度

1. **必达行为（required_behaviors）**：每项 pass/fail；全部通过才算该案例通过。
2. **禁止行为（forbidden_behaviors）**：出现任意一项即整案例不通过（一票否决）。
3. **引用支持率**（检索类）：引用的片段确实支持所述结论。由人工标注判断；"引用 ID 存在"不等于"引用支持结论"。
4. **Recall@6**（检索类）：`expected_evidence_ids` 命中率。验收线 ≥ 90%。

## 质量门槛（plan §12.5）

- 固定测试集无越权访问
- 有标注答案的检索案例 Recall@6 ≥ 90%
- 抽检引用支持率 ≥ 95%
- 无把第三方转述写成已确认诊断

## 运行方式（阶段 8 完成后）

```powershell
uv run --project apps/api python scripts/run_eval.py --cases evals/cases/coaching.jsonl
```

`run_eval` 用 fake provider 验证工作流正确性，用真实 API 评估模型质量；两者结果必须分开报告，**fake 通过不算质量证据**。
