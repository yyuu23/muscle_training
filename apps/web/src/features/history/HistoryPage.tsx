/**
 * History page (plan §8.1 训练历史页): date-grouped sessions, plan vs
 * actual comparison, online corrections with version-conflict handling.
 */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLiveQuery } from 'dexie-react-hooks';
import { ChevronDownIcon, PencilSquareIcon } from '@heroicons/react/24/outline';
import { db } from '../../offline/database';
import type { LocalWorkoutSession } from '../../offline/types';
import { apiFetch, APIError } from '../../api/client';
import { useAuth } from '../auth/useAuth';
import { useSyncStatus } from '../../hooks/useSync';
import { EmptyState } from '../../components/ErrorState';

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
      await apiFetch(`/workouts/sets/${correction.setId}`, {
        method: 'PATCH',
        body: {
          expected_version: correction.expected_version,
          load_kg: correction.load_kg || null,
          reps: correction.reps,
          rir: correction.rir,
          reason: '在线更正（用户请求）',
        },
      });
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
    <div className="max-w-lg mx-auto px-4 py-6 space-y-5">
      <h1 className="text-2xl font-bold text-gray-900">训练历史</h1>

      {!isOnline && (
        <p className="text-xs text-gray-400">
          离线中：展示本机缓存记录；在线更正需联网后操作。
        </p>
      )}
      {correctionMessage && (
        <div className="card p-3 text-sm text-gray-700 bg-gray-50">{correctionMessage}</div>
      )}

      {grouped.length === 0 ? (
        <div className="card p-6">
          <EmptyState
            title="还没有训练记录"
            description="开始训练后会在这里按日期查看"
            action={<button onClick={() => navigate('/today')} className="btn-primary px-4 py-2 text-sm">去开始训练</button>}
          />
        </div>
      ) : (
        grouped.map(([date, daySessions]) => (
          <div key={date}>
            <p className="text-xs text-gray-400 mb-2 px-1">
              {new Date(date).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'long' })}
            </p>
            <div className="space-y-2">
              {(daySessions ?? []).map((session) => {
                const expanded = expandedId === session.id;
                return (
                  <div key={session.id} className="card overflow-hidden">
                    <button
                      className="w-full p-4 flex items-center justify-between text-left"
                      onClick={() => setExpandedId(expanded ? null : session.id)}
                    >
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {session.plan_day_key ?? '自由训练'}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {new Date(session.started_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                          {session.completed_at &&
                            ` – ${new Date(session.completed_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`}
                          {session.pending_sync && ' · 待同步'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            session.status === 'completed'
                              ? 'bg-green-50 text-green-700'
                              : session.status === 'in_progress'
                                ? 'bg-blue-50 text-blue-600'
                                : 'bg-gray-100 text-gray-400'
                          }`}
                        >
                          {session.status === 'completed' ? '完成' : session.status === 'in_progress' ? '进行中' : '放弃'}
                        </span>
                        <ChevronDownIcon className={`w-4 h-4 text-gray-300 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                      </div>
                    </button>

                    {expanded && (
                      <div className="border-t border-gray-50 p-4 space-y-3">
                        {expandedId === session.id && detail && (
                          <>
                            {detail.exercises.map((ex) => {
                              const exSets = detail.sets.filter((s) => s.session_exercise_id === ex.id);
                              return (
                                <div key={ex.id}>
                                  <div className="flex items-center justify-between mb-1">
                                    <p className="text-xs font-medium text-gray-600">{ex.exercise_id.slice(0, 8)}…</p>
                                    <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                      ex.completion_status === 'completed' ? 'bg-green-50 text-green-600'
                                        : ex.completion_status === 'skipped' ? 'bg-gray-100 text-gray-400'
                                        : 'bg-amber-50 text-amber-600'
                                    }`}>
                                      {ex.completion_status === 'completed' ? '完成' : ex.completion_status === 'skipped' ? '跳过' : '部分记录'}
                                    </span>
                                  </div>
                                  <ul className="space-y-1">
                                    {exSets.map((s) => (
                                      <li key={s.id} className="flex items-center justify-between text-xs bg-gray-50 rounded-lg px-3 py-1.5">
                                        <span className="text-gray-400">第{s.set_index}组</span>
                                        <span className="text-gray-700">
                                          {s.status === 'skipped' ? '跳过' : (
                                            <>
                                              {s.load_kg ? `${s.load_kg}kg` : '—'} × {s.reps ?? '—'}
                                              {s.rir !== null && <span className="text-gray-400"> RIR{s.rir}</span>}
                                            </>
                                          )}
                                        </span>
                                        {isOnline && session.status === 'completed' && s.status !== 'skipped' && (
                                          <button
                                            className="text-primary-500"
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
                                      <li className="text-xs text-gray-300 px-3">未记录组（区别于跳过）</li>
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
      )}

      {/* Correction dialog */}
      {correction && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full space-y-3">
            <h3 className="font-semibold">更正记录</h3>
            <p className="text-xs text-gray-400">需要填写更正原因并带版本号提交；旧复盘会标记过期。</p>
            <input
              type="number" step="0.5" placeholder="重量 kg"
              value={correction.load_kg}
              onChange={(e) => setCorrection({ ...correction, load_kg: e.target.value })}
              className="input w-full"
            />
            <input
              type="number" placeholder="次数"
              value={correction.reps ?? ''}
              onChange={(e) => setCorrection({ ...correction, reps: e.target.value ? parseInt(e.target.value, 10) : null })}
              className="input w-full"
            />
            <input
              type="number" placeholder="RIR（可空）" min="0" max="10"
              value={correction.rir ?? ''}
              onChange={(e) => setCorrection({ ...correction, rir: e.target.value ? parseInt(e.target.value, 10) : null })}
              className="input w-full"
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setCorrection(null)} className="px-4 py-2 text-sm rounded-lg border border-gray-200">取消</button>
              <button onClick={submitCorrection} className="btn-primary px-4 py-2 text-sm">提交更正</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
