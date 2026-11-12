# 生成训练计划（版本：generate_plan-v1）

## 任务目标
基于用户档案与已审核模板，生成一份训练计划候选。计划最终必须由用户采用；你的输出只是草稿。

## 输入字段
- profile: 用户档案（目标、经验、每周次数、单次时长、器械、可用星期、重量增量）
- constraints[]: 已确认限制与偏好
- template: 已审核模板（允许的动作、组次/次数/休息范围、进阶策略）
- allowed_exercises[]: 可用动作卡（slug、名称、负荷模式、计量类型、替代动作）
- recent_training: 近期可比较训练摘要

## 输出类型
```json
{
  "title": "...",
  "goal": "...",
  "template_slug": "...",
  "days": [
    {
      "day_key": "day_1",
      "weekday": 1,
      "estimated_minutes": 60,
      "exercises": [
        {
          "exercise_slug": "...",
          "working_sets": 3,
          "reps_min": 8, "reps_max": 12,
          "duration_seconds": null,
          "rest_seconds": 120,
          "target_rir": 2,
          "initial_load_kg": null,
          "load_instruction": "首次训练记录实际重量，不要推算",
          "reason": "选择该动作的理由"
        }
      ]
    }
  ],
  "notes": "校准与安全说明"
}
```

## 缺失信息处理
- 没有适用模板或可用动作时，不要编造计划；返回错误说明内容未就绪。
- 用户档案缺少必要字段时列出 missing_fields，不虚构。
- 初始负荷未知时 initial_load_kg 必须为 null，并给出校准说明；禁止根据身高体重推算起始重量。

## 不允许的行为
- 只能使用 allowed_exercises 和 template 范围内的动作；不得发明新动作或新 slug。
- 不得使用 constraints 中用户明确排除的动作或器械。
- 不得突破模板的组次、次数、休息范围。
- 次数型与时长型目标互斥，不能同时填写。
- 计划天数必须等于模板 sessions_per_week，安排在 available_weekdays 内。
- 你的输出不直接生效：不写「已启用」「已替换旧计划」之类的表述。

## 引用格式
reason 字段说明依据（模板要求、限制、近期记录）；不引用知识片段 ID，引用由系统校验后附加。

## 事实、建议和推断的区分
整份计划都是「建议草稿」，需用户采用后生效；reason 中引用档案与模板的部分是「事实依据」。
