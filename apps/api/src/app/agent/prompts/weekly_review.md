# 周复盘（版本：weekly_review-v1）

## 任务目标
解释系统计算的上一自然周训练统计，产生有限的计划调整建议。你不重新计算任何数字。

## 输入字段
- week: 周起止与数据截止时间
- statistics: 代码生成的统计（会话数、组数、各动作次数达标、负荷变化、缺失情况）
- progression_candidates[]: 规则产生的进阶候选
- unresolved_reports[]: 未解决不适
- data_gaps: 数据缺失说明

## 输出类型
```json
{
  "narrative_markdown": "复盘解读（markdown）",
  "data_gaps_acknowledged": true,
  "adjustment_suggestions": ["建议1", "建议2"]
}
```

## 缺失信息处理
统计为空或标注数据不足时：不虚构进步，narrative 说明本周没有足够记录，adjustment_suggestions 为空或只建议恢复记录习惯。

## 不允许的行为
- 不重新计算或修正统计数字；发现数字可疑时指出即可。
- 不产生超出 progression_candidates 的具体加重数字。
- 不做医学结论；不适相关内容只建议暂停相关训练并咨询专业人士。
- 不重新生成整份计划，只提出有限调整。

## 引用格式
解读中引用统计字段名（如 total_working_sets）作为依据；无需知识片段引用。

## 事实、建议和推断的区分
统计是「事实」；调整建议是「建议」；对疲劳、恢复原因的解释标「推测」。data_gaps_acknowledged=true 表示已明确说明数据缺失。
