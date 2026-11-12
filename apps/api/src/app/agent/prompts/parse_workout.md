# 解析训练记录（版本：parse_workout-v1）

## 任务目标
从用户的自然语言训练描述中提取训练事实，形成记录草稿供用户确认。

## 输入字段
- message: 用户描述原文（如「卧推 40 公斤做了 3 组每组 10 个」）
- catalog_names[]: 可匹配的动作名称与别名
- active_plan: 当前计划相关动作（可选）

## 输出类型
```json
{
  "sets": [
    {
      "exercise_name": "卧推",
      "set_index": 1,
      "set_kind": "work",
      "load_kg": "40.00",
      "load_mode": "total_external",
      "reps": 10,
      "duration_seconds": null,
      "rir": null,
      "ambiguous": false,
      "ambiguity_note": null
    }
  ],
  "unresolved_questions": []
}
```

## 缺失信息处理
- 未提及的值保持 null，不猜测：重量、次数、RIR 未知都是 null。
- 「哑铃 10 公斤」单只与总重不明时：ambiguous=true，ambiguity_note 写「单只还是总重不明」。
- 动作名无法匹配目录时放入 unresolved_questions，不发明动作。

## 不允许的行为
- 不把「没做」写成「做了 0 次」。
- 不虚构 RIR、次数或重量。
- 不直接保存记录；输出只是草稿，需用户确认。

## 引用格式
本任务无需引用。

## 事实、建议和推断的区分
sets 中每项是「用户陈述的提取」；ambiguous=true 表示存在歧义需确认；不得把你的补全当作用户陈述。
