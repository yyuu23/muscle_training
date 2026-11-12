/**
 * PlanDiff — old vs new plan changes with reasons and adopt button
 * (plan §4.7 / §8.1)
 */

import { ArrowUpIcon, ArrowDownIcon, PlusIcon, MinusIcon } from '@heroicons/react/24/outline';

export interface DiffEntry {
  kind: 'exercise_added' | 'exercise_removed' | 'exercise_modified';
  item_id: string;
  exercise_id?: string;
  changes?: Record<string, { old: unknown; new: unknown }>;
}

export interface PlanDiffData {
  title_changed?: boolean;
  goal_changed?: boolean;
  day_changes: {
    day_key: string;
    kind: 'day_added' | 'day_removed' | 'day_modified';
    items: DiffEntry[];
    estimated_minutes?: { old: number | null; new: number | null };
  }[];
}

const FIELD_LABELS: Record<string, string> = {
  working_sets: '组数',
  reps_min: '次数下限',
  reps_max: '次数上限',
  duration_seconds: '时长(秒)',
  rest_seconds: '休息(秒)',
  initial_load_kg: '初始负荷(kg)',
};

const DAY_LABELS: Record<number, string> = {
  1: '周一', 2: '周二', 3: '周三', 4: '周四', 5: '周五', 6: '周六', 7: '周日',
};

export function PlanDiff({ diff }: { diff: PlanDiffData | null }) {
  if (!diff || diff.day_changes.length === 0) {
    return <p className="text-sm text-gray-400">与当前计划没有结构性差异。</p>;
  }

  return (
    <div className="space-y-4">
      {diff.day_changes.map((day) => (
        <div key={day.day_key} className="border border-gray-100 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="font-medium text-sm text-gray-900">{day.day_key}</span>
            {day.kind === 'day_added' && (
              <span className="text-xs bg-green-50 text-green-700 px-2 py-0.5 rounded-full">新增训练日</span>
            )}
            {day.kind === 'day_removed' && (
              <span className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded-full">移除训练日</span>
            )}
            {day.estimated_minutes && (
              <span className="text-xs text-gray-500">
                时长 {day.estimated_minutes.old ?? '—'} → {day.estimated_minutes.new} 分钟
              </span>
            )}
          </div>

          <ul className="space-y-2">
            {day.items.map((item) => (
              <li key={item.item_id} className="flex items-start gap-2 text-sm">
                {item.kind === 'exercise_added' && (
                  <PlusIcon className="w-4 h-4 text-green-600 mt-0.5 shrink-0" />
                )}
                {item.kind === 'exercise_removed' && (
                  <MinusIcon className="w-4 h-4 text-red-600 mt-0.5 shrink-0" />
                )}
                {item.kind === 'exercise_modified' && (
                  <ArrowUpIcon className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
                )}
                <div className="flex-1">
                  <span className="text-gray-700">{item.item_id}</span>
                  {item.changes && (
                    <div className="mt-1 flex flex-wrap gap-2">
                      {Object.entries(item.changes).map(([field, change]) => (
                        <span
                          key={field}
                          className="text-xs bg-gray-50 border border-gray-100 rounded px-2 py-0.5 text-gray-600"
                        >
                          {FIELD_LABELS[field] ?? field}:
                          <span className="text-gray-400 line-through mx-1">
                            {String(change.old ?? '空')}
                          </span>
                          <ArrowDownIcon className="w-3 h-3 inline rotate-[-90deg]" />
                          <span className="text-gray-900 font-medium mx-1">
                            {String(change.new ?? '空')}
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </li>
            ))}
            {day.items.length === 0 && day.kind === 'day_modified' && (
              <li className="text-xs text-gray-400">仅时长调整</li>
            )}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function weekdayLabel(weekday: number): string {
  return DAY_LABELS[weekday] ?? `星期${weekday}`;
}
