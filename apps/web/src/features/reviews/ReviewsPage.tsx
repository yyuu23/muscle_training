/**
 * Weekly reviews page (plan §8.1 周复盘页): statistics, data cutoff,
 * narrative, adjustment candidates, stale banner + regenerate.
 */

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowPathIcon, ExclamationTriangleIcon } from '@heroicons/react/24/solid';
import { apiFetch } from '../../api/client';
import { EmptyState, ErrorState } from '../../components/ErrorState';
import { Button } from '../../components/ui/Button';
import { SkeletonCards } from '../../components/ui/Skeleton';

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

function StatCard({ label, value, delay = 0 }: { label: string; value: string | number; delay?: number }) {
  return (
    <div className="bg-surface-2 rounded-2xl p-3 text-center animate-slide-up" style={{ animationDelay: `${delay}ms` }}>
      <p className="text-xl font-bold text-text tabular-nums animate-count-pop" key={value}>{value}</p>
      <p className="text-xs text-text-muted mt-0.5">{label}</p>
    </div>
  );
}

/** Mini bar chart: working sets per session this week. */
function SessionBars({ details }: { details: { started_at: string; total_working_sets: number }[] }) {
  if (!details.length) return null;
  const max = Math.max(...details.map((d) => d.total_working_sets), 1);
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold mb-3">每次训练工作组数</h3>
      <div className="flex items-end gap-2 h-28">
        {details.map((d, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1.5 min-w-0">
            <span className="text-[10px] text-text-muted tabular-nums">{d.total_working_sets}</span>
            <div
              className="w-full rounded-t-lg bg-gradient-to-t from-primary to-primary-400 transition-[height] duration-700 ease-out"
              style={{ height: `${(d.total_working_sets / max) * 100}%`, transitionDelay: `${i * 80}ms` }}
              title={`${new Date(d.started_at).toLocaleDateString('zh-CN')} · ${d.total_working_sets} 组`}
            />
            <span className="text-[10px] text-text-muted truncate w-full text-center">
              {new Date(d.started_at).toLocaleDateString('zh-CN', { weekday: 'short' })}
            </span>
          </div>
        ))}
      </div>
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

  if (isLoading) return <div className="page-container py-6"><SkeletonCards count={3} /></div>;
  if (isError) return <div className="page-container py-6"><ErrorState message="无法加载复盘" onRetry={() => void refetch()} /></div>;

  const reviews = data?.items ?? [];
  const selected = selectedId ? reviews.find((r) => r.id === selectedId) : reviews[0];

  return (
    <div className="page-container py-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text">周复盘</h1>
        <Button size="sm" onClick={() => generate.mutate()} loading={generate.isPending}>
          {!generate.isPending && <ArrowPathIcon className="w-4 h-4" />}
          {generate.isPending ? '生成中…' : '生成本周复盘'}
        </Button>
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
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin">
            {reviews.map((r) => (
              <button
                key={r.id}
                onClick={() => setSelectedId(r.id)}
                className={`shrink-0 px-3.5 py-2 rounded-xl text-xs border transition-all ${
                  selected?.id === r.id
                    ? 'border-primary bg-primary-soft text-primary font-semibold shadow-soft'
                    : 'border-border-default text-text-secondary hover:border-border-strong'
                }`}
              >
                {weekLabel(r.week_start)}
                {r.stale && ' · 已过期'}
              </button>
            ))}
          </div>

          {selected && (
            <div className="space-y-4 xl:grid xl:grid-cols-[340px_minmax(0,1fr)] xl:gap-5 xl:items-start xl:space-y-0">
              <div className="space-y-4">
              {selected.stale && (
                <div className="card p-4 !border-warning/30 !bg-warning-soft flex items-center justify-between gap-3 animate-scale-in">
                  <p className="text-sm text-warning flex items-center gap-2">
                    <ExclamationTriangleIcon className="w-4 h-4 shrink-0" />
                    生成后有迟到日志或更正，此复盘基于旧数据
                  </p>
                  <button
                    onClick={() => regenerate.mutate(selected.id)}
                    disabled={regenerate.isPending}
                    className="btn btn-sm text-xs shrink-0 !bg-warning !text-white hover:brightness-95"
                  >
                    重新生成
                  </button>
                </div>
              )}

              <div className="grid grid-cols-2 xl:grid-cols-1 gap-2.5">
                <StatCard
                  label="完成训练"
                  value={`${selected.statistics.sessions_completed ?? 0}/${selected.statistics.planned_days ?? selected.statistics.sessions_total ?? 0}`}
                  delay={0}
                />
                <StatCard label="总工作组数" value={selected.statistics.total_working_sets ?? 0} delay={60} />
                <StatCard label="总次数" value={selected.statistics.total_working_reps ?? 0} delay={120} />
                <StatCard
                  label="体重变化"
                  value={
                    selected.statistics.weight_first != null && selected.statistics.weight_last != null
                      ? `${(selected.statistics.weight_last - selected.statistics.weight_first).toFixed(1)}kg`
                      : '—'
                  }
                  delay={180}
                />
              </div>
              </div>

              <div className="space-y-4">
              {selected.statistics.session_details && selected.statistics.session_details.length > 0 && (
                <SessionBars details={selected.statistics.session_details} />
              )}

              <div className="card p-5 animate-slide-up" style={{ animationDelay: '120ms' }}>
                <p className="text-xs text-text-muted mb-2.5">
                  数据截至 {new Date(selected.data_cutoff_at).toLocaleString('zh-CN')}
                  {' '}· 数据修订 {selected.data_revision}
                </p>
                {selected.narrative ? (
                  <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">{selected.narrative}</div>
                ) : (
                  <EmptyState title="本周没有足够记录，未生成分析" description="恢复记录后可重新生成" />
                )}
              </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
