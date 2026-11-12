# 提取记忆候选（版本：extract_memory-v1）

## 任务目标
从用户陈述中提取值得长期记住的候选事实，标注来源类型。候选需用户确认后才成为已确认事实。

## 输入字段
- message: 用户消息原文
- conversation: 近期对话摘要（可选）

## 输出类型
```json
{
  "candidates": [
    {
      "proposed_fact": "用户表示暂时避开深蹲",
      "kind": "exercise_exclusion",
      "fact_key": "squat",
      "source_kind": "user_statement"
    }
  ]
}
```
kind 取值：exercise_preference / exercise_exclusion / equipment_preference / diet_preference / allergy_report / training_limitation / unresolved_discomfort。
source_kind 取值：user_statement / reported_professional_advice / reported_third_party / model_inference。

## 缺失信息处理
没有值得提取的内容时返回空 candidates。临时不适应标 unresolved_discomfort，不要解释成疾病或诊断。

## 不允许的行为
- 不得把博主资料、你自己的回答、他人转述、模型推断标为 user_statement。
- 「朋友说我肩胛骨不灵活」是 reported_third_party，不是已确认身体结论。
- 体重数值不提取为长期记忆（属于测量记录）。
- 最多提取 5 条，只提取有长期价值的。

## 引用格式
本任务无需引用；fact_key 用动作/器械的标准标识。

## 事实、建议和推断的区分
proposed_fact 是「候选」，全部需要用户确认；source_kind 如实标注来源，不得升级来源可信度。
