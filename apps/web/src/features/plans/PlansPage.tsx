/**
 * Plans page (plan §8.1 计划页): current plan, drafts, version history,
 * generation trigger, adopt entry.
 */

import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SparklesIcon, ClockIcon } from '@heroicons/react/24/outline';
import { apiFetch, APIError } from '../../api/client';
import { EmptyState, ErrorState } from '../../components/ErrorState';
import { useJobPolling } from './useJobPolling';

interface PlanSummary {
  id: string;
  sequence_number: number;
  status: 'draft' | 'active' | 'superseded' | 'archived';
  content: { title?: string; goal?: string; days?: { day_key: string }[] };
  created_at: string;
  activated_at: string | null;
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿', active: '生效中', superseded: '已替代', archived: '已归档',
};

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-amber-50 text-amber-700',
  active: 'bg-green-50 text-green-700',
  superseded: 'bg-gray-100 text-gray-500',
  archived: 'bg-gray-100 text-gray-400',
};

export function PlansPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const activeQuery = useQuery({
    queryKey: ['plans', 'active'],
    queryFn: () => apiFetch<{ plan: PlanSummary | null }>('/plans/active'),
  });

  const listQuery = useQuery({
    queryKey: ['plans', 'list'],
    queryFn: () => apiFetch<{ items: PlanSummary[] }>('/plans'),
  });

  const job = useJobPolling(jobId);

  // Generation finished → refresh the list
  if (job?.status === 'succeeded') {
    void queryClient.invalidateQueries({ queryKey: ['plans'] });
  }

  const generate = async () => {
    setGenerateError(null);
    try {
      const result = await apiFetch<{ job_id: string }>('/plans/generate', { method: 'POST' });
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
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">我的计划</h1>
        <button onClick={generate} disabled={generating} className="btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm">
          <SparklesIcon className="w-4 h-4" />
          {generating ? '生成中…' : '生成新计划'}
        </button>
      </div>

      {generateError && (
        <div className="card p-4 text-sm text-amber-700 bg-amber-50 border-amber-100">{generateError}</div>
      )}

      {generating && (
        <div className="card p-4 text-sm text-gray-600 flex items-center gap-2">
          <ClockIcon className="w-4 h-4 animate-pulse text-primary-600" />
          正在基于你的档案和已审核模板生成计划候选（任务阶段：{job?.phase ?? job?.status ?? '排队中'}）…
        </div>
      )}

      {job?.status === 'succeeded' && (
        <div className="card p-4 text-sm text-green-700 bg-green-50 border-green-100">
          计划草稿已生成，
          <button
            className="underline font-medium"
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
        <div className="card p-4 text-sm text-red-700 bg-red-50 border-red-100">
          生成失败：{job.error_code ?? '未知错误'}
        </div>
      )}

      {/* Active plan */}
      {activeQuery.isLoading ? (
        <div className="card p-6 text-sm text-gray-400">加载中…</div>
      ) : activeQuery.isError ? (
        <ErrorState message="无法加载当前计划" onRetry={() => void activeQuery.refetch()} />
      ) : activeQuery.data?.plan ? (
        <Link to={`/plans/${activeQuery.data.plan.id}`} className="card p-5 block hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold text-gray-900">{activeQuery.data.plan.content.title ?? '当前计划'}</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLES.active}`}>
              {STATUS_LABELS.active}
            </span>
          </div>
          <p className="text-sm text-gray-500">{activeQuery.data.plan.content.goal}</p>
          <p className="text-xs text-gray-400 mt-2">
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
      <div className="card p-5">
        <h2 className="font-semibold text-gray-900 mb-3">版本历史</h2>
        {listQuery.isLoading ? (
          <p className="text-sm text-gray-400">加载中…</p>
        ) : listQuery.data?.items.length ? (
          <ul className="divide-y divide-gray-50">
            {listQuery.data.items.map((plan) => (
              <li key={plan.id}>
                <Link to={`/plans/${plan.id}`} className="flex items-center justify-between py-3 hover:bg-gray-50 -mx-2 px-2 rounded">
                  <div>
                    <p className="text-sm font-medium text-gray-800">
                      v{plan.sequence_number} · {plan.content.title ?? '未命名计划'}
                    </p>
                    <p className="text-xs text-gray-400">
                      {new Date(plan.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_STYLES[plan.status] ?? ''}`}>
                    {STATUS_LABELS[plan.status] ?? plan.status}
                  </span>
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
