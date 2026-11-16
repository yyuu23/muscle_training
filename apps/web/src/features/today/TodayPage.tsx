/**
 * Today page (plan §8.1 今日训练页): today's plan day preview,
 * pre-training check (unresolved discomfort → explicit ask),
 * start/continue workout.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLiveQuery } from 'dexie-react-hooks';
import {
  PlusIcon, FireIcon, ExclamationTriangleIcon, ChevronRightIcon, ClockIcon,
} from '@heroicons/react/24/outline';
import { db } from '../../offline/database';
import { workoutActions, useActiveSession } from '../workouts/useWorkoutSession';
import { useAuth } from '../auth/useAuth';
import { useSyncStatus } from '../../hooks/useSync';
import { ActiveSessionCard } from './ActiveSessionCard';
import { QuickStats } from './QuickStats';
import { Badge } from '../../components/ui/Badge';
import { EmptyState } from '../../components/ErrorState';
import { weekdayLabel } from '../../components/PlanDiff';

interface PlanDayPreview {
  day_key: string;
  weekday: number;
  estimated_minutes: number;
  exercises: { exercise_snapshot: { name?: string; slug?: string }; working_sets: number; reps_min: number | null; reps_max: number | null; duration_seconds: number | null }[];
}

export function TodayPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { status, pendingCount } = useSyncStatus(user?.id ?? null);
  const activeSession = useActiveSession(user?.id ?? null);
  const [precheckAnswers, setPrecheckAnswers] = useState<Record<string, unknown> | null>(null);
  const [showPrecheck, setShowPrecheck] = useState(false);

  const plan = useLiveQuery(
    async () => {
      if (!user) return null;
      const plans = await db.plans
        .where('owner_user_id')
        .equals(user.id)
        .and((p) => p.status === 'active')
        .toArray();
      return plans[0] ?? null;
    },
    [user?.id],
  );

  const unresolvedDiscomfort = useLiveQuery(
    async () => {
      if (!user) return [];
      return db.profileFacts
        .where('owner_user_id')
        .equals(user.id)
        .and((f) => f.kind === 'unresolved_discomfort')
        .toArray();
    },
    [user?.id],
  );

  const recentSessions = useLiveQuery(
    async () => {
      if (!user) return [];
      const cutoff = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString();
      return db.workoutSessions
        .where('owner_user_id')
        .equals(user.id)
        .and((s) => s.started_at >= cutoff)
        .reverse()
        .sortBy('started_at');
    },
    [user?.id],
  );

  const todayWeekday = new Date().getDay() === 0 ? 7 : new Date().getDay();

  const todayDay: PlanDayPreview | null = useMemo(() => {
    if (!plan?.content?.days) return null;
    const days = plan.content.days as PlanDayPreview[];
    return days.find((d) => d.weekday === todayWeekday) ?? null;
  }, [plan, todayWeekday]);

  const startWorkout = () => {
    if (!user) return;
    const hasDiscomfort = (unresolvedDiscomfort ?? []).length > 0;
    if (hasDiscomfort && !precheckAnswers) {
      setShowPrecheck(true);
      return;
    }
    void performStart(user.id);
  };

  return (
    <div className="min-h-screen pb-24 lg:pb-10">
      {/* Hero header */}
      <div className="page-header pt-8 pb-14 rounded-b-[2rem] relative overflow-hidden">
        {/* decorative glow */}
        <div
          className="absolute -top-24 -right-16 w-64 h-64 rounded-full opacity-20 blur-3xl pointer-events-none"
          style={{ background: 'radial-gradient(circle, #a5b4fc, transparent 70%)' }}
          aria-hidden
        />
        <div className="page-container relative">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium tracking-widest uppercase opacity-70">TODAY</span>
            {status === 'offline' ? (
              <Badge tone="warning">离线模式 · 本机记录</Badge>
            ) : pendingCount > 0 ? (
              <Badge tone="primary">{pendingCount} 条待同步</Badge>
            ) : (
              <Badge tone="success">已同步</Badge>
            )}
          </div>
          <h1 className="text-3xl font-bold mb-1.5">今日训练</h1>
          <p className="page-header-muted text-sm">
            {new Date().toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
      </div>

      <div className="page-container lg:grid lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-6 lg:items-start lg:space-y-0 space-y-4">
        {/* only the main column overlaps the hero header (-mt-8); the
            stats rail starts below the header curve on desktop */}
        <div className="space-y-4 -mt-8">
        {activeSession ? (
          <ActiveSessionCard session={activeSession} />
        ) : showPrecheck ? (
          <div className="card p-5 space-y-3 animate-scale-in border-l-4" style={{ borderLeftColor: 'var(--warning)' }}>
            <div className="flex items-center gap-2 text-warning">
              <ExclamationTriangleIcon className="w-5 h-5" />
              <h2 className="font-semibold text-text">训练前确认</h2>
            </div>
            {(unresolvedDiscomfort ?? []).map((f) => (
              <p key={f.id} className="text-sm text-text-secondary">· {f.value}</p>
            ))}
            <p className="text-sm text-text-muted">之前的未解决不适是否已恢复？</p>
            <div className="flex gap-2">
              <button
                className="btn btn-primary flex-1 py-2.5 text-sm"
                onClick={() => {
                  setPrecheckAnswers({ checked: true, recovered: true });
                  setShowPrecheck(false);
                  if (user) void performStart(user.id);
                }}
              >
                已恢复，正常训练
              </button>
              <button
                className="btn btn-secondary flex-1 py-2.5 text-sm !border-warning/40 !text-warning"
                onClick={() => {
                  setPrecheckAnswers({ checked: true, recovered: false });
                  setShowPrecheck(false);
                  if (user) void performStart(user.id);
                }}
              >
                仍有不适（记录后继续）
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={startWorkout}
            className="group w-full btn btn-primary btn-lg shadow-glow !rounded-2xl relative overflow-hidden"
          >
            <span
              className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-out bg-gradient-to-r from-transparent via-white/25 to-transparent pointer-events-none"
              aria-hidden
            />
            <PlusIcon className="w-6 h-6" />
            <span className="text-lg tracking-wide">开始训练</span>
            <FireIcon className="w-5 h-5 opacity-80" />
          </button>
        )}

        {/* Today's plan day */}
        {todayDay ? (
          <div className="card p-5 animate-slide-up" style={{ animationDelay: '60ms' }}>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold flex items-center gap-2">
                今日计划
                <Badge tone="primary">{weekdayLabel(todayDay.weekday)}</Badge>
              </h2>
              <span className="text-xs text-text-muted inline-flex items-center gap-1">
                <ClockIcon className="w-3.5 h-3.5" /> 约 {todayDay.estimated_minutes} 分钟
              </span>
            </div>
            <ul className="space-y-2">
              {todayDay.exercises.map((ex, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between text-sm bg-surface-2 rounded-xl px-3 py-2.5 animate-slide-up"
                  style={{ animationDelay: `${120 + i * 50}ms` }}
                >
                  <span className="text-text">{ex.exercise_snapshot?.name ?? ex.exercise_snapshot?.slug}</span>
                  <span className="text-xs text-text-muted tabular-nums">
                    {ex.working_sets} 组 ×{' '}
                    {ex.duration_seconds ? `${ex.duration_seconds}秒` : `${ex.reps_min}–${ex.reps_max} 次`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : plan ? (
          <div className="card p-4 text-sm text-text-muted text-center animate-fade-in">
            今天（{weekdayLabel(todayWeekday)}）不是计划训练日；也可以自由训练。
          </div>
        ) : null}
        </div>

        <div className="space-y-4">
        <QuickStats />

        <div className="card !p-0 overflow-hidden animate-slide-up" style={{ animationDelay: '180ms' }}>
          <div className="flex items-center justify-between px-5 pt-5 pb-3">
            <h2 className="text-base font-semibold">最近记录</h2>
            <button
              onClick={() => navigate('/history')}
              className="text-sm text-primary font-medium inline-flex items-center gap-0.5 hover:gap-1.5 transition-all"
            >
              查看全部 <ChevronRightIcon className="w-4 h-4" />
            </button>
          </div>
          {(recentSessions ?? []).length === 0 ? (
            <EmptyState
              title="暂无训练记录"
              description="开始你的第一次训练吧！"
            />
          ) : (
            <ul className="divide-y divide-border-default/60">
              {(recentSessions ?? []).slice(0, 3).map((s, i) => (
                <li
                  key={s.id}
                  className="py-3 px-5 flex items-center justify-between animate-slide-up"
                  style={{ animationDelay: `${220 + i * 50}ms` }}
                >
                  <div>
                    <p className="text-sm text-text">
                      {new Date(s.started_at).toLocaleDateString('zh-CN')}
                      {s.plan_day_key && ` · ${s.plan_day_key}`}
                    </p>
                    <p className="text-xs text-text-secondary mt-0.5">
                      {s.status === 'completed' ? '✓ 已完成' : s.status === 'in_progress' ? '进行中' : '已放弃'}
                    </p>
                  </div>
                  {s.pending_sync && <Badge tone="primary">待同步</Badge>}
                </li>
              ))}
            </ul>
          )}
        </div>
        </div>
      </div>
    </div>
  );

  async function performStart(uid: string) {
    await workoutActions.start(uid, {
      plan_version_id: plan?.id ?? null,
      plan_day_key: todayDay?.day_key ?? null,
      precheck: precheckAnswers ?? { checked: true },
    });
    const latest = await db.workoutSessions
      .where('owner_user_id')
      .equals(uid)
      .reverse()
      .sortBy('started_at');
    if (latest[0]) navigate(`/workouts/${latest[0].id}`);
  }
}
