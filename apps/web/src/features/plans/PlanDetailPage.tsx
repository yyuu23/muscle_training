/**
 * Plan detail page: body, basis versions, validation issues, diff vs
 * active and explicit adoption (plan §6.3 / §8.1).
 */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeftIcon, CheckIcon } from '@heroicons/react/24/outline';
import { apiFetch, APIError } from '../../api/client';
import { ErrorState } from '../../components/ErrorState';
import { PlanDiff, type PlanDiffData, weekdayLabel } from '../../components/PlanDiff';
import { ConfirmAction } from '../../components/ConfirmAction';

interface PlanDetail {
  plan: {
    id: string;
    sequence_number: number;
    status: string;
    content: {
      title: string;
      goal: string;
      timezone: string;
      days: {
        day_key: string;
        weekday: number;
        estimated_minutes: number;
        exercises: {
          item_id: string;
          exercise_snapshot: { name?: string; slug?: string };
          working_sets: number;
          reps_min: number | null;
          reps_max: number | null;
          duration_seconds: number | null;
          rest_seconds: number;
          initial_load_kg: string | null;
          load_instruction: string | null;
        }[];
      }[];
    };
    basis_profile_version: number | null;
    basis_planning_revision: number | null;
    rationale: string | null;
  };
  validation_issues: { code: string; message: string }[];
  diff_vs_active: PlanDiffData | null;
}

export function PlanDetailPage() {
  const { planId } = useParams<{ planId: string }>();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['plans', planId],
    queryFn: () => apiFetch<PlanDetail>(`/plans/${planId}`),
    enabled: !!planId,
  });

  const adopt = async () => {
    setError(null);
    try {
      const snapshot = await apiFetch<{ planning_revision: number }>('/sync/snapshot');
      await apiFetch(`/plans/${planId}/activate`, {
        method: 'POST',
        body: { expected_basis_planning_revision: snapshot.planning_revision },
      });
      await queryClient.invalidateQueries({ queryKey: ['plans'] });
    } catch (err) {
      if (err instanceof APIError) {
        if (err.code === 'PLAN_CONTEXT_STALE') {
          setError('候选计划所依据的数据已变化（档案或训练记录已更新），请重新生成计划。');
        } else if (err.code === 'MODEL_OUTPUT_INVALID') {
          setError('计划未通过约束校验，不能采用。');
        } else {
          setError(err.message);
        }
      } else {
        setError('采用失败，请重试');
      }
      await refetch();
    }
  };

  if (isLoading) return <div className="max-w-2xl mx-auto px-4 py-6 text-sm text-gray-400">加载中…</div>;
  if (isError || !data) return <div className="max-w-2xl mx-auto px-4 py-6"><ErrorState message="计划不存在或无法加载" onRetry={() => void refetch()} /></div>;

  const { plan } = data;

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <Link to="/plans" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800">
        <ArrowLeftIcon className="w-4 h-4" /> 返回计划列表
      </Link>

      <div>
        <h1 className="text-2xl font-bold text-gray-900">{plan.content.title}</h1>
        <p className="text-sm text-gray-500 mt-1">
          v{plan.sequence_number} · {plan.content.goal}
        </p>
      </div>

      {error && <div className="card p-4 text-sm text-red-700 bg-red-50 border-red-100">{error}</div>}

      {/* Basis versions */}
      <div className="card p-4 text-xs text-gray-500">
        依据：档案版本 {plan.basis_profile_version ?? '—'} · planning_revision {plan.basis_planning_revision ?? '—'}
        {plan.rationale && <p className="mt-1 text-gray-600">{plan.rationale}</p>}
      </div>

      {/* Validation issues */}
      {data.validation_issues.length > 0 && (
        <div className="card p-4 border-amber-100 bg-amber-50">
          <p className="text-sm font-medium text-amber-800 mb-1">校验问题（{data.validation_issues.length}）</p>
          <ul className="text-xs text-amber-700 space-y-1">
            {data.validation_issues.map((issue, i) => (
              <li key={i}>· {issue.message}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Days */}
      <div className="space-y-4">
        {plan.content.days.map((day) => (
          <div key={day.day_key} className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">
                {day.day_key} · {weekdayLabel(day.weekday)}
              </h3>
              <span className="text-xs text-gray-400">约 {day.estimated_minutes} 分钟</span>
            </div>
            <ul className="space-y-3">
              {day.exercises.map((ex) => (
                <li key={ex.item_id} className="border border-gray-50 rounded-xl p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-gray-800">
                      {ex.exercise_snapshot?.name ?? ex.exercise_snapshot?.slug ?? ex.item_id}
                    </span>
                    <span className="text-xs text-gray-500">
                      {ex.working_sets} 组 ×{' '}
                      {ex.duration_seconds
                        ? `${ex.duration_seconds} 秒`
                        : `${ex.reps_min}–${ex.reps_max} 次`}
                      {' '}· 休息 {ex.rest_seconds}s
                    </span>
                  </div>
                  {ex.initial_load_kg === null && (
                    <p className="text-xs text-amber-600 mt-1">
                      初始负荷未知：{ex.load_instruction ?? '首次训练记录实际重量进行校准，不要推算'}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Diff vs active */}
      {plan.status === 'draft' && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 mb-3">与当前计划的差异</h3>
          <PlanDiff diff={data.diff_vs_active} />
        </div>
      )}

      {/* Adopt */}
      {plan.status === 'draft' && data.validation_issues.length === 0 && (
        <ConfirmAction
          title="采用这个计划？"
          description="采用后当前生效计划将变为历史版本；新计划立即生效。这一操作只能由你确认执行。"
          confirmLabel="采用计划"
          onConfirm={adopt}
        >
          {(trigger) => (
            <button onClick={trigger} className="btn-primary w-full py-3 inline-flex items-center justify-center gap-2">
              <CheckIcon className="w-5 h-5" /> 采用此计划
            </button>
          )}
        </ConfirmAction>
      )}
    </div>
  );
}
