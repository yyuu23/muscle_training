/**
 * Plans page (plan §8.1 计划页): current plan, drafts, version history,
 * generation trigger, adopt entry.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SparklesIcon, ClockIcon, ChevronRightIcon } from '@heroicons/react/24/solid';
import { APIError, apiGet, apiPost } from '../../api/client';
import { EmptyState, ErrorState } from '../../components/ErrorState';
import { useJobPolling } from './useJobPolling';
import { Badge } from '../../components/ui/Badge';
import type { BadgeTone } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { useTilt } from '../../hooks/useTilt';

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿', active: '生效中', superseded: '已替代', archived: '已归档',
};

const STATUS_TONES: Record<string, BadgeTone> = {
  draft: 'warning', active: 'success', superseded: 'neutral', archived: 'neutral',
};

export function PlansPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const tilt = useTilt<HTMLAnchorElement>(4);

  const activeQuery = useQuery({
    queryKey: ['plans', 'active'],
    queryFn: () => apiGet('/api/v1/plans/active'),
  });

  const listQuery = useQuery({
    queryKey: ['plans', 'list'],
    queryFn: () => apiGet('/api/v1/plans'),
  });

  const job = useJobPolling(jobId);

  // Generation finished → refresh the list
  if (job?.status === 'succeeded') {
    void queryClient.invalidateQueries({ queryKey: ['plans'] });
  }

  const generate = async () => {
    setGenerateError(null);
    try {
      const result = await apiPost('/api/v1/plans/generate');
      setJobId(result.job_id);
    } catch (err) {
      if (err instanceof APIError) {
        if (err.code === 'CONTENT_NOT_READY') {
          setGenerateError('内容未就绪：还没有已审核的训练模板，请联系管理员导入并审核内容。');
          return;
        }
        if (err.code === 'INSUFFICIENT_PROFILE') {
          setGenerateError('档案信息不足，请先完成建档。');
          navigate('/onboarding');
          return;
        }
        if (err.code === 'BUDGET_EXHAUSTED') {
          setGenerateError('本月 AI 预算已用完；记录功能不受影响。');
          return;
        }
      }
      setGenerateError(err instanceof Error ? err.message : '生成任务创建失败');
    }
  };

  const generating = jobId !== null && job !== null &&
    ['queued', 'running', 'waiting_external'].includes(job.status);

  return (
    <div className="page-container py-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text">我的计划</h1>
        <Button size="sm" onClick={generate} disabled={generating}>
          <SparklesIcon className="w-4 h-4" />
          {generating ? '生成中…' : '生成新计划'}
        </Button>
      </div>

      {generateError && (
        <div className="card p-4 text-sm text-warning !bg-warning-soft !border-warning/30 animate-scale-in">{generateError}</div>
      )}

      {generating && (
        <div className="card p-4 text-sm text-text-secondary flex items-center gap-2.5 animate-fade-in">
          <ClockIcon className="w-4 h-4 animate-pulse text-primary" />
          正在基于你的档案和已审核模板生成计划候选（任务阶段：{job?.phase ?? job?.status ?? '排队中'}）…
        </div>
      )}

      {job?.status === 'succeeded' && (
        <div className="card p-4 text-sm text-success !bg-success-soft !border-success/30 animate-scale-in">
          计划草稿已生成，
          <button
            className="underline font-semibold"
            onClick={() => {
              const planId = (job.result_ref?.plan_draft_id as string) || '';
              if (planId) navigate(`/plans/${planId}`);
            }}
          >
            查看并采用
          </button>
        </div>
      )}

      {job?.status === 'failed' && (
        <div className="card p-4 text-sm text-danger !bg-danger-soft !border-danger/30 animate-scale-in">
          生成失败：{job.error_code ?? '未知错误'}
        </div>
      )}

      {/* Active plan */}
      {activeQuery.isLoading ? (
        <SkeletonCards count={1} />
      ) : activeQuery.isError ? (
        <ErrorState message="无法加载当前计划" onRetry={() => void activeQuery.refetch()} />
      ) : activeQuery.data?.plan ? (
        <Link
          ref={tilt.ref}
          onMouseMove={tilt.onMouseMove}
          onMouseLeave={tilt.onMouseLeave}
          to={`/plans/${activeQuery.data.plan.id}`}
          className="card card-interactive p-5 block !border-primary/25 relative overflow-hidden"
        >
          <div
            className="absolute -top-14 -right-10 w-44 h-44 rounded-full opacity-[0.12] blur-2xl pointer-events-none"
            style={{ background: 'radial-gradient(circle, var(--primary), transparent 70%)' }}
            aria-hidden
          />
          <div className="flex items-center justify-between mb-2 relative">
            <h2 className="font-semibold text-text">{activeQuery.data.plan.content.title ?? '当前计划'}</h2>
            <div className="flex items-center gap-1">
              <Badge tone="success">{STATUS_LABELS.active}</Badge>
              <ChevronRightIcon className="w-4 h-4 text-text-muted" />
            </div>
          </div>
          <p className="text-sm text-text-secondary">{activeQuery.data.plan.content.goal}</p>
          <p className="text-xs text-text-muted mt-2">
            每周 {activeQuery.data.plan.content.days?.length ?? 0} 个训练日
          </p>
        </Link>
      ) : (
        <div className="card p-6">
          <EmptyState
            title="还没有生效计划"
            description="完成建档后点击「生成新计划」，模型会基于已审核模板生成草稿，由你确认后采用"
          />
        </div>
      )}

      {/* Version history */}
      <div className="card p-5 animate-slide-up" style={{ animationDelay: '80ms' }}>
        <h2 className="font-semibold text-text mb-3">版本历史</h2>
        {listQuery.isLoading ? (
          <p className="text-sm text-text-muted">加载中…</p>
        ) : listQuery.data?.items.length ? (
          <ul className="divide-y divide-border-default/60 -mx-2">
            {listQuery.data.items.map((plan, i) => (
              <li key={plan.id} className="animate-fade-in" style={{ animationDelay: `${i * 40}ms` }}>
                <Link
                  to={`/plans/${plan.id}`}
                  className="flex items-center justify-between py-3 px-2 -mx-2 rounded-xl hover:bg-surface-2 transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium text-text">
                      v{plan.sequence_number} · {plan.content.title ?? '未命名计划'}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">
                      {new Date(plan.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge tone={STATUS_TONES[plan.status] ?? 'neutral'}>
                      {STATUS_LABELS[plan.status] ?? plan.status}
                    </Badge>
                    <ChevronRightIcon className="w-4 h-4 text-text-muted" />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="暂无历史计划" />
        )}
      </div>
    </div>
  );
}
