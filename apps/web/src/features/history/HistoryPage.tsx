/**
 * History page (plan §8.1 训练历史页): date-grouped sessions, plan vs
 * actual comparison, online corrections with version-conflict handling.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLiveQuery } from 'dexie-react-hooks';
import { ChevronDownIcon, PencilSquareIcon } from '@heroicons/react/24/solid';
import { db } from '../../offline/database';
import type { LocalWorkoutSession } from '../../offline/types';
import { APIError, apiPatch } from '../../api/client';
import { useAuth } from '../auth/useAuth';
import { useSyncStatus } from '../../hooks/useSync';
import { EmptyState } from '../../components/ErrorState';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Sheet } from '../../components/ui/Sheet';
import { SkeletonCards } from '../../components/ui/Skeleton';

interface CorrectionDraft {
  setId: string;
  expected_version: number;
  load_kg: string;
  reps: number | null;
  rir: number | null;
}

export function HistoryPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { isOnline } = useSyncStatus(user?.id ?? null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [correction, setCorrection] = useState<CorrectionDraft | null>(null);
  const [correctionMessage, setCorrectionMessage] = useState<string | null>(null);

  const sessions = useLiveQuery(
    async () => {
      if (!user) return [];
      return db.workoutSessions
        .where('owner_user_id')
        .equals(user.id)
        .reverse()
        .sortBy('started_at');
    },
    [user?.id],
  );

  const grouped = useMemo(() => {
    const groups = new Map<string, LocalWorkoutSession[]>();
    for (const session of sessions ?? []) {
      const key = session.started_at.slice(0, 10);
      const list = groups.get(key);
      if (list) {
        list.push(session);
      } else {
        groups.set(key, [session]);
      }
    }
    return Array.from(groups.entries());
  }, [sessions]);

  const detail = useLiveQuery(
    async () => {
      if (!expandedId) return null;
      const exercises = await db.sessionExercises.where('session_id').equals(expandedId).sortBy('position');
      const sets = exercises.length
        ? await db.workoutSets.where('session_exercise_id').anyOf(exercises.map((e) => e.id)).sortBy('set_index')
        : [];
      return { exercises, sets };
    },
    [expandedId],
  );

  const submitCorrection = async () => {
    if (!correction) return;
    setCorrectionMessage(null);
    try {
      await apiPatch(
        '/api/v1/workouts/sets/{set_id}',
        {
          expected_version: correction.expected_version,
          load_kg: correction.load_kg || null,
          reps: correction.reps,
          rir: correction.rir,
          reason: '在线更正（用户请求）',
        },
        { set_id: correction.setId },
      );
      setCorrection(null);
      setCorrectionMessage('已更正；相关复盘已标记过期。');
    } catch (err) {
      if (err instanceof APIError && err.code === 'VERSION_CONFLICT') {
        setCorrectionMessage('记录已被其他设备修改，请刷新后重试。');
      } else {
        setCorrectionMessage(err instanceof Error ? err.message : '更正失败');
      }
    }
  };

  return (
    <div className="page-container py-6 space-y-5">
      <h1 className="text-2xl font-bold text-text">训练历史</h1>

      {!isOnline && (
        <p className="text-xs text-text-muted">
          离线中：展示本机缓存记录；在线更正需联网后操作。
        </p>
      )}
      {correctionMessage && (
        <div className="card !py-3 text-sm text-text-secondary !bg-primary-soft animate-scale-in">{correctionMessage}</div>
      )}

      {sessions === undefined ? (
        <SkeletonCards count={3} />
      ) : grouped.length === 0 ? (
        <div className="card p-6">
          <EmptyState
            title="还没有训练记录"
            description="开始训练后会在这里按日期查看"
            action={<Button size="sm" onClick={() => navigate('/today')}>去开始训练</Button>}
          />
        </div>
      ) : (
        <div className="space-y-5 lg:columns-2 lg:gap-5 lg:space-y-0">
        {grouped.map(([date, daySessions], gi) => (
          <div key={date} className="animate-slide-up lg:mb-5 break-inside-avoid" style={{ animationDelay: `${gi * 60}ms` }}>
            <p className="text-xs text-text-muted mb-2 px-1 font-medium">
              {new Date(date).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}
            </p>
            <div className="space-y-2.5">
              {(daySessions ?? []).map((session) => {
                const expanded = expandedId === session.id;
                return (
                  <div key={session.id} className="card card-solid !p-0 overflow-hidden">
                    <button
                      className="w-full p-4 flex items-center justify-between text-left"
                      onClick={() => setExpandedId(expanded ? null : session.id)}
                    >
                      <div>
                        <p className="text-sm font-medium text-text">
                          {session.plan_day_key ?? '自由训练'}
                        </p>
                        <p className="text-xs text-text-muted mt-0.5">
                          {new Date(session.started_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                          {session.completed_at &&
                            ` – ${new Date(session.completed_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`}
                          {session.pending_sync && ' · 待同步'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge tone={
                          session.status === 'completed' ? 'success'
                            : session.status === 'in_progress' ? 'primary' : 'neutral'
                        }>
                          {session.status === 'completed' ? '完成' : session.status === 'in_progress' ? '进行中' : '放弃'}
                        </Badge>
                        <ChevronDownIcon
                          className={`w-4 h-4 text-text-muted transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
                        />
                      </div>
                    </button>

                    {expanded && (
                      <div className="border-t border-border-default p-4 space-y-3 animate-fade-in">
                        {expandedId === session.id && detail && (
                          <>
                            {detail.exercises.map((ex, exIdx) => {
                              const exSets = detail.sets.filter((s) => s.session_exercise_id === ex.id);
                              return (
                                <div key={ex.id} className="animate-slide-up" style={{ animationDelay: `${exIdx * 50}ms` }}>
                                  <div className="flex items-center justify-between mb-1.5">
                                    <p className="text-xs font-medium text-text-secondary">{ex.exercise_id.slice(0, 8)}…</p>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                      ex.completion_status === 'completed' ? 'bg-success-soft text-success'
                                        : ex.completion_status === 'skipped' ? 'bg-surface-2 text-text-muted'
                                        : 'bg-warning-soft text-warning'
                                    }`}>
                                      {ex.completion_status === 'completed' ? '完成' : ex.completion_status === 'skipped' ? '跳过' : '部分记录'}
                                    </span>
                                  </div>
                                  <ul className="space-y-1">
                                    {exSets.map((s) => (
                                      <li key={s.id} className="flex items-center justify-between text-xs bg-surface-2 rounded-xl px-3 py-2">
                                        <span className="text-text-muted">第{s.set_index}组</span>
                                        <span className="text-text tabular-nums">
                                          {s.status === 'skipped' ? '跳过' : (
                                            <>
                                              {s.load_kg ? `${s.load_kg}kg` : '—'} × {s.reps ?? '—'}
                                              {s.rir !== null && <span className="text-text-muted"> RIR{s.rir}</span>}
                                            </>
                                          )}
                                        </span>
                                        {isOnline && session.status === 'completed' && s.status !== 'skipped' && (
                                          <button
                                            className="text-primary hover:scale-110 transition-transform"
                                            title="在线更正"
                                            onClick={() =>
                                              setCorrection({
                                                setId: s.id,
                                                expected_version: s.version,
                                                load_kg: s.load_kg ?? '',
                                                reps: s.reps,
                                                rir: s.rir,
                                              })
                                            }
                                          >
                                            <PencilSquareIcon className="w-3.5 h-3.5" />
                                          </button>
                                        )}
                                      </li>
                                    ))}
                                    {exSets.length === 0 && (
                                      <li className="text-xs text-text-muted px-3 py-1">未记录组（区别于跳过）</li>
                                    )}
                                  </ul>
                                </div>
                              );
                            })}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))
        }
        </div>
      )}

      {/* Correction sheet */}
      <Sheet open={!!correction} onClose={() => setCorrection(null)} title="更正记录">
        <p className="text-xs text-text-muted mb-3">需要填写更正原因并带版本号提交；旧复盘会标记过期。</p>
        <div className="space-y-2.5">
          <input
            type="number" step="0.5" placeholder="重量 kg"
            value={correction?.load_kg ?? ''}
            onChange={(e) => correction && setCorrection({ ...correction, load_kg: e.target.value })}
            className="input tabular-nums"
          />
          <input
            type="number" placeholder="次数"
            value={correction?.reps ?? ''}
            onChange={(e) => correction && setCorrection({ ...correction, reps: e.target.value ? parseInt(e.target.value, 10) : null })}
            className="input tabular-nums"
          />
          <input
            type="number" placeholder="RIR（可空）" min="0" max="10"
            value={correction?.rir ?? ''}
            onChange={(e) => correction && setCorrection({ ...correction, rir: e.target.value ? parseInt(e.target.value, 10) : null })}
            className="input tabular-nums"
          />
        </div>
        <div className="flex gap-2 mt-4">
          <Button variant="secondary" className="flex-1" onClick={() => setCorrection(null)}>取消</Button>
          <Button className="flex-1" onClick={submitCorrection}>提交更正</Button>
        </div>
      </Sheet>
    </div>
  );
}
