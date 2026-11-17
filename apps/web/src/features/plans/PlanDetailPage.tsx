/**
 * Plan detail page: body, basis versions, validation issues, diff vs
 * active and explicit adoption (plan §6.3 / §8.1).
 */

import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeftIcon, CheckIcon } from '@heroicons/react/24/solid';
import { APIError, apiGet, apiPost } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { ErrorState } from '../../components/ErrorState';
import { PlanDiff, type PlanDiffData, weekdayLabel } from '../../components/PlanDiff';
import { ConfirmAction } from '../../components/ConfirmAction';
import { Badge } from '../../components/ui/Badge';
import { SkeletonCards } from '../../components/ui/Skeleton';

/** Contract type with the free-form diff narrowed to the view model. */
type PlanDetail = Omit<components['schemas']['PlanDetailResponse'], 'diff_vs_active'> & {
  diff_vs_active: PlanDiffData | null;
};

export function PlanDetailPage() {
  const { planId } = useParams<{ planId: string }>();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['plans', planId],
    queryFn: async (): Promise<PlanDetail> => {
      const detail = await apiGet('/api/v1/plans/{plan_id}', { plan_id: planId! });
      return { ...detail, diff_vs_active: (detail.diff_vs_active ?? null) as PlanDiffData | null };
    },
    enabled: !!planId,
  });

  const adopt = async () => {
    setError(null);
    try {
      const snapshot = await apiGet('/api/v1/sync/snapshot');
      await apiPost(
        '/api/v1/plans/{plan_id}/activate',
        { expected_basis_planning_revision: snapshot.planning_revision },
        { plan_id: planId! },
      );
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

  if (isLoading) return <div className="page-container py-6"><SkeletonCards count={3} /></div>;
  if (isError || !data) return <div className="page-container py-6"><ErrorState message="计划不存在或无法加载" onRetry={() => void refetch()} /></div>;

  const { plan } = data;

  return (
    <div className="page-container py-6 space-y-5">
      <Link to="/plans" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text transition-colors">
        <ArrowLeftIcon className="w-4 h-4" /> 返回计划列表
      </Link>

      <div className="animate-slide-up">
        <div className="flex items-center gap-2.5">
          <h1 className="text-2xl font-bold text-text">{plan.content.title}</h1>
          <Badge tone={plan.status === 'active' ? 'success' : plan.status === 'draft' ? 'warning' : 'neutral'}>
            {plan.status === 'active' ? '生效中' : plan.status === 'draft' ? '草稿' : plan.status}
          </Badge>
        </div>
        <p className="text-sm text-text-secondary mt-1">
          v{plan.sequence_number} · {plan.content.goal}
        </p>
      </div>

      {error && <div className="card p-4 text-sm text-danger !bg-danger-soft !border-danger/30 animate-scale-in">{error}</div>}

      {/* Basis versions */}
      <div className="card !p-4 text-xs text-text-muted !bg-surface-2 animate-fade-in">
        依据：档案版本 {plan.basis_profile_version ?? '—'} · planning_revision {plan.basis_planning_revision ?? '—'}
        {plan.rationale && <p className="mt-1.5 text-text-secondary">{plan.rationale}</p>}
      </div>

      {/* Validation issues */}
      {data.validation_issues.length > 0 && (
        <div className="card p-4 !border-warning/30 !bg-warning-soft animate-scale-in">
          <p className="text-sm font-medium text-warning mb-1">校验问题（{data.validation_issues.length}）</p>
          <ul className="text-xs text-warning/90 space-y-1">
            {data.validation_issues.map((issue, i) => (
              <li key={i}>· {issue.message}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Days */}
      <div className="space-y-4 lg:grid lg:grid-cols-2 lg:gap-4 lg:space-y-0">
        {plan.content.days.map((day, di) => (
          <div key={day.day_key} className="card p-5 animate-slide-up" style={{ animationDelay: `${di * 70}ms` }}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-text">
                {day.day_key} · {weekdayLabel(day.weekday)}
              </h3>
              <span className="text-xs text-text-muted">约 {day.estimated_minutes} 分钟</span>
            </div>
            <ul className="space-y-2.5">
              {day.exercises.map((ex, i) => (
                <li
                  key={ex.item_id}
                  className="border border-border-default rounded-2xl p-3.5 bg-surface animate-fade-in"
                  style={{ animationDelay: `${i * 40}ms` }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-sm text-text">
                      {ex.exercise_snapshot?.name ?? ex.exercise_snapshot?.slug ?? ex.item_id}
                    </span>
                    <span className="text-xs text-text-secondary tabular-nums">
                      {ex.working_sets} 组 ×{' '}
                      {ex.duration_seconds
                        ? `${ex.duration_seconds} 秒`
                        : `${ex.reps_min}–${ex.reps_max} 次`}
                      {' '}· 休息 {ex.rest_seconds}s
                    </span>
                  </div>
                  {ex.initial_load_kg === null && (
                    <p className="text-xs text-warning mt-1.5">
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
        <div className="card p-5 animate-slide-up">
          <h3 className="font-semibold text-text mb-3">与当前计划的差异</h3>
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
            <button onClick={trigger} className="btn btn-primary btn-lg w-full shadow-glow">
              <CheckIcon className="w-5 h-5" /> 采用此计划
            </button>
          )}
        </ConfirmAction>
      )}
    </div>
  );
}
