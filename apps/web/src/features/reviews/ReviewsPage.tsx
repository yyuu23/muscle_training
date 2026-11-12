/**
 * Weekly reviews page (plan §8.1 周复盘页): statistics, data cutoff,
 * narrative, adjustment candidates, stale banner + regenerate.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowPathIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { apiFetch } from '../../api/client';
import { EmptyState, ErrorState } from '../../components/ErrorState';

interface WeeklyReview {
  id: string;
  week_start: string;
  data_cutoff_at: string;
  data_revision: number;
  stale: boolean;
  statistics: {
    sessions_completed?: number;
    sessions_total?: number;
    planned_days?: number | null;
    total_working_sets?: number;
    total_working_reps?: number;
    skipped_exercises?: number;
    weight_first?: number | null;
    weight_last?: number | null;
    data_sufficient?: boolean;
    session_details?: { started_at: string; total_working_sets: number }[];
  };
  narrative: string | null;
  created_at: string;
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-50 rounded-xl p-3 text-center">
      <p className="text-xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  );
}

function weekLabel(weekStart: string): string {
  const start = new Date(weekStart);
  const end = new Date(start.getTime() + 6 * 24 * 3600 * 1000);
  return `${start.toLocaleDateString('zh-CN')} – ${end.toLocaleDateString('zh-CN')}`;
}

export function ReviewsPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['reviews', 'weekly'],
    queryFn: () => apiFetch<{ items: WeeklyReview[] }>('/reviews/weekly'),
  });

  const generate = useMutation({
    mutationFn: () => apiFetch<WeeklyReview>('/reviews/weekly', { method: 'POST', body: {} }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews'] }),
  });

  const regenerate = useMutation({
    mutationFn: (id: string) =>
      apiFetch<WeeklyReview>(`/reviews/weekly/${id}/regenerate`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reviews'] }),
  });

  if (isLoading) return <div className="max-w-2xl mx-auto px-4 py-6 text-sm text-gray-400">加载中…</div>;
  if (isError) return <div className="max-w-2xl mx-auto px-4 py-6"><ErrorState message="无法加载复盘" onRetry={() => void refetch()} /></div>;

  const reviews = data?.items ?? [];
  const selected = selectedId ? reviews.find((r) => r.id === selectedId) : reviews[0];

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">周复盘</h1>
        <button
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
          className="btn-primary px-4 py-2 text-sm inline-flex items-center gap-2"
        >
          <ArrowPathIcon className={`w-4 h-4 ${generate.isPending ? 'animate-spin' : ''}`} />
          {generate.isPending ? '生成中…' : '生成本周复盘'}
        </button>
      </div>

      {reviews.length === 0 ? (
        <div className="card p-6">
          <EmptyState
            title="还没有复盘"
            description="每周一自动生成上一自然周的复盘；也可以随时手动生成"
          />
        </div>
      ) : (
        <>
          {/* Review selector */}
          <div className="flex gap-2 overflow-x-auto pb-1">
            {reviews.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={`shrink-0 px-3 py-2 rounded-xl text-xs border ${
                  selected?.id === r.id
                    ? 'border-primary-500 bg-primary-50 text-primary-700 font-medium'
                    : 'border-gray-200 text-gray-600'
                }`}
              >
                {weekLabel(r.week_start)}
                {r.stale && ' ·已过期'}
              </button>
            ))}
          </div>

          {selected && (
            <div className="space-y-4">
              {selected.stale && (
                <div className="card p-4 border-amber-100 bg-amber-50 flex items-center justify-between gap-3">
                  <p className="text-sm text-amber-800 flex items-center gap-2">
                    <ExclamationTriangleIcon className="w-4 h-4 shrink-0" />
                    生成后有迟到日志或更正，此复盘基于旧数据
                  </p>
                  <button
                    onClick={() => regenerate.mutate(selected.id)}
                    disabled={regenerate.isPending}
                    className="text-xs px-3 py-1.5 rounded-lg bg-amber-600 text-white shrink-0"
                  >
                    重新生成
                  </button>
                </div>
              )}

              <div className="grid grid-cols-4 gap-2">
                <StatCard label="完成训练" value={`${selected.statistics.sessions_completed ?? 0}/${selected.statistics.planned_days ?? selected.statistics.sessions_total ?? 0}`} />
                <StatCard label="总工作组数" value={selected.statistics.total_working_sets ?? 0} />
                <StatCard label="总次数" value={selected.statistics.total_working_reps ?? 0} />
                <StatCard
                  label="体重变化"
                  value={
                    selected.statistics.weight_first != null && selected.statistics.weight_last != null
                      ? `${(selected.statistics.weight_last - selected.statistics.weight_first).toFixed(1)}kg`
                      : '—'
                  }
                />
              </div>

              <div className="card p-5">
                <p className="text-xs text-gray-400 mb-2">
                  数据截至 {new Date(selected.data_cutoff_at).toLocaleString('zh-CN')}
                  {' '}· 数据修订 {selected.data_revision}
                </p>
                {selected.narrative ? (
                  <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">{selected.narrative}</div>
                ) : (
                  <EmptyState title="本周没有足够记录，未生成分析" description="恢复记录后可重新生成" />
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
