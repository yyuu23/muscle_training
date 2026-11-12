/**
 * Today page (plan §8.1 今日训练页): today's plan day preview,
 * pre-training check (unresolved discomfort → explicit ask),
 * start/continue workout.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLiveQuery } from 'dexie-react-hooks';
import { PlusIcon, FireIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { db } from '../../offline/database';
import { workoutActions, useActiveSession } from '../workouts/useWorkoutSession';
import { useAuth } from '../auth/useAuth';
import { useSyncStatus } from '../../hooks/useSync';
import { ActiveSessionCard } from './ActiveSessionCard';
import { QuickStats } from './QuickStats';
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
    <div className="min-h-screen bg-gradient-to-b from-primary-50 to-gray-50 pb-24">
      <div className="bg-primary-600 text-white px-4 pt-8 pb-12 rounded-b-3xl shadow-strong">
        <div className="max-w-md mx-auto">
          <h1 className="text-3xl font-bold mb-2">今日训练</h1>
          <p className="text-primary-100 text-sm">
            {new Date().toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            {status === 'offline' && ' · 离线模式（记录保存在本机）'}
            {status !== 'offline' && pendingCount > 0 && ` · ${pendingCount} 条待同步`}
          </p>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 -mt-6 space-y-4">
        {activeSession ? (
          <ActiveSessionCard session={activeSession} />
        ) : showPrecheck ? (
          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2 text-amber-700">
              <ExclamationTriangleIcon className="w-5 h-5" />
              <h2 className="font-semibold">训练前确认</h2>
            </div>
            {(unresolvedDiscomfort ?? []).map((f) => (
              <p key={f.id} className="text-sm text-gray-600">· {f.value}</p>
            ))}
            <p className="text-sm text-gray-500">之前的未解决不适是否已恢复？</p>
            <div className="flex gap-2">
              <button
                className="btn-primary flex-1 py-2 text-sm"
                onClick={() => {
                  setPrecheckAnswers({ checked: true, recovered: true });
                  setShowPrecheck(false);
                  if (user) void performStart(user.id);
                }}
              >
                已恢复，正常训练
              </button>
              <button
                className="flex-1 py-2 text-sm rounded-xl border border-amber-200 text-amber-700"
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
            className="w-full btn-primary btn-lg shadow-strong flex items-center justify-center gap-3 hover:shadow-xl transform hover:-translate-y-0.5"
          >
            <PlusIcon className="w-6 h-6" />
            <span className="text-lg">开始训练</span>
            <FireIcon className="w-5 h-5" />
          </button>
        )}

        {/* Today's plan day */}
        {todayDay ? (
          <div className="card p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold flex items-center gap-2">
                今日计划 · {weekdayLabel(todayDay.weekday)}
              </h2>
              <span className="text-xs text-gray-400">约 {todayDay.estimated_minutes} 分钟</span>
            </div>
            <ul className="space-y-2">
              {todayDay.exercises.map((ex, i) => (
                <li key={i} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{ex.exercise_snapshot?.name ?? ex.exercise_snapshot?.slug}</span>
                  <span className="text-xs text-gray-400">
                    {ex.working_sets} 组 ×{' '}
                    {ex.duration_seconds ? `${ex.duration_seconds}秒` : `${ex.reps_min}–${ex.reps_max} 次`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ) : plan ? (
          <div className="card p-4 text-sm text-gray-500 text-center">
            今天（{weekdayLabel(todayWeekday)}）不是计划训练日；也可以自由训练。
          </div>
        ) : null}

        <QuickStats />

        <div className="card">
          <div className="flex items-center justify-between mb-3 px-5 pt-5">
            <h2 className="text-lg font-semibold">最近记录</h2>
            <button onClick={() => navigate('/history')} className="text-sm text-primary-600 font-medium">
              查看全部
            </button>
          </div>
          {(recentSessions ?? []).length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p className="text-sm">暂无训练记录</p>
              <p className="text-xs mt-1">开始你的第一次训练吧！</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-50 px-5 pb-3">
              {(recentSessions ?? []).slice(0, 3).map((s) => (
                <li key={s.id} className="py-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-800">
                      {new Date(s.started_at).toLocaleDateString('zh-CN')}
                      {s.plan_day_key && ` · ${s.plan_day_key}`}
                    </p>
                    <p className="text-xs text-gray-400">
                      {s.status === 'completed' ? '已完成' : s.status === 'in_progress' ? '进行中' : '已放弃'}
                    </p>
                  </div>
                  {s.pending_sync && <span className="text-[10px] text-primary-500">待同步</span>}
                </li>
              ))}
            </ul>
          )}
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
