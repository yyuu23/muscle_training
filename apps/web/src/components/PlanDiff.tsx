/**
 * PlanDiff — old vs new plan changes with reasons and adopt button
 * (plan §4.7 / §8.1)
 */

import { ArrowUpIcon, ArrowDownIcon, PlusIcon, MinusIcon } from '@heroicons/react/24/solid';
import { Badge } from './ui/Badge';

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
    return <p className="text-sm text-text-muted">与当前计划没有结构性差异。</p>;
  }

  return (
    <div className="space-y-3">
      {diff.day_changes.map((day, di) => (
        <div
          key={day.day_key}
          className="border border-border-default rounded-2xl p-4 animate-slide-up"
          style={{ animationDelay: `${di * 60}ms` }}
        >
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span className="font-medium text-sm text-text">{day.day_key}</span>
            {day.kind === 'day_added' && <Badge tone="success">新增训练日</Badge>}
            {day.kind === 'day_removed' && <Badge tone="danger">移除训练日</Badge>}
            {day.estimated_minutes && (
              <span className="text-xs text-text-muted">
                时长 {day.estimated_minutes.old ?? '—'} → {day.estimated_minutes.new} 分钟
              </span>
            )}
          </div>

          <ul className="space-y-2">
            {day.items.map((item, i) => (
              <li
                key={item.item_id}
                className="flex items-start gap-2 text-sm animate-fade-in"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                {item.kind === 'exercise_added' && (
                  <span className="mt-0.5 shrink-0 w-5 h-5 rounded-lg bg-success-soft text-success inline-flex items-center justify-center">
                    <PlusIcon className="w-3 h-3" />
                  </span>
                )}
                {item.kind === 'exercise_removed' && (
                  <span className="mt-0.5 shrink-0 w-5 h-5 rounded-lg bg-danger-soft text-danger inline-flex items-center justify-center">
                    <MinusIcon className="w-3 h-3" />
                  </span>
                )}
                {item.kind === 'exercise_modified' && (
                  <span className="mt-0.5 shrink-0 w-5 h-5 rounded-lg bg-warning-soft text-warning inline-flex items-center justify-center">
                    <ArrowUpIcon className="w-3 h-3" />
                  </span>
                )}
                <div className="flex-1 min-w-0">
                  <span className="text-text-secondary">{item.item_id}</span>
                  {item.changes && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {Object.entries(item.changes).map(([field, change]) => (
                        <span
                          key={field}
                          className="text-xs bg-surface-2 border border-border-default rounded-lg px-2 py-1 text-text-secondary"
                        >
                          {FIELD_LABELS[field] ?? field}:
                          <span className="text-text-muted line-through mx-1">
                            {String(change.old ?? '空')}
                          </span>
                          <ArrowDownIcon className="w-3 h-3 inline rotate-[-90deg] text-primary" />
                          <span className="text-text font-semibold mx-1">
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
              <li className="text-xs text-text-muted">仅时长调整</li>
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
