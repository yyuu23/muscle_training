/**
 * Session page (plan §8.1 训练记录页): per-set logging with load/reps/
 * RIR, rest timer, temporary substitution, completion. Offline-first:
 * every write is local + outbox.
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useLiveQuery } from 'dexie-react-hooks';
import { CheckIcon, ClockIcon, PlusIcon, FireIcon } from '@heroicons/react/24/outline';
import { db } from '../../offline/database';
import { workoutActions, useWorkoutSession } from './useWorkoutSession';
import { useAuth } from '../auth/useAuth';
import { EmptyState } from '../../components/ErrorState';
import { useSyncStatus } from '../../hooks/useSync';

function RestTimer({ seconds, onDone }: { seconds: number; onDone: () => void }) {
  const [remaining, setRemaining] = useState(seconds);

  useEffect(() => {
    setRemaining(seconds);
  }, [seconds]);

  useEffect(() => {
    if (remaining <= 0) {
      onDone();
      return;
    }
    const timer = setTimeout(() => setRemaining((r) => r - 1), 1000);
    return () => clearTimeout(timer);
  }, [remaining, onDone]);

  const display = `${String(Math.floor(remaining / 60)).padStart(2, '0')}:${String(remaining % 60).padStart(2, '0')}`;
  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-40 bg-gray-900 text-white px-5 py-3 rounded-2xl shadow-xl flex items-center gap-2">
      <ClockIcon className="w-5 h-5 text-primary-300" />
      <span className="font-mono text-lg font-semibold">{display}</span>
      <span className="text-xs text-gray-400">休息中</span>
    </div>
  );
}

export function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { status, pendingCount } = useSyncStatus(user?.id ?? null);
  const userId = user?.id ?? '';

  const { session, exercises, sets } = useWorkoutSession(id ?? null);
  const catalog = useLiveQuery(() => db.exercises.toArray(), []);

  const [restSeconds, setRestSeconds] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [discomfortPrompt, setDiscomfortPrompt] = useState<string | null>(null);

  const exerciseById = useMemo(() => new Map((catalog ?? []).map((e) => [e.id, e])), [catalog]);

  const setsByExercise = useMemo(() => {
    const map = new Map<string, typeof sets>();
    for (const s of sets ?? []) {
      const list = map.get(s.session_exercise_id) ?? [];
      list.push(s);
      map.set(s.session_exercise_id, list);
    }
    return map;
  }, [sets]);

  if (!session) {
    return (
      <div className="max-w-lg mx-auto px-4 py-10">
        <EmptyState title="训练不存在" action={
          <button onClick={() => navigate('/today')} className="btn-primary px-4 py-2 text-sm">返回今日</button>
        } />
      </div>
    );
  }

  if (session.status !== 'in_progress') {
    return (
      <div className="max-w-lg mx-auto px-4 py-10 space-y-4">
        <div className="card p-6 text-center">
          <CheckIcon className="w-10 h-10 text-green-500 mx-auto mb-2" />
          <p className="font-semibold">训练已完成</p>
          <p className="text-sm text-gray-500 mt-1">
            {new Date(session.started_at).toLocaleString('zh-CN')} · {(sets ?? []).length} 组
          </p>
        </div>
        <button onClick={() => navigate('/history')} className="btn-primary w-full py-3 text-sm">
          查看历史记录
        </button>
      </div>
    );
  }

  const logSet = (
    sessionExerciseId: string,
    setIndex: number,
    input: Omit<Parameters<typeof workoutActions.logSet>[2], 'set_index'>,
    restSeconds?: number,
  ) => {
    void workoutActions.logSet(userId, sessionExerciseId, { ...input, set_index: setIndex });
    if (restSeconds && input.status !== 'skipped') setRestSeconds(restSeconds);
  };

  return (
    <div className="max-w-lg mx-auto px-4 py-5 pb-28 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">训练中</h1>
          <p className="text-xs text-gray-400">
            {new Date(session.started_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })} 开始
            {status === 'offline' ? ' · 离线记录中' : pendingCount > 0 ? ` · ${pendingCount} 条待同步` : ''}
          </p>
        </div>
        <button
          onClick={async () => {
            await workoutActions.complete(userId, session.id, discomfortPrompt);
            navigate('/today');
          }}
          className="btn-primary px-4 py-2 text-sm inline-flex items-center gap-1"
        >
          <CheckIcon className="w-4 h-4" /> 完成训练
        </button>
      </div>

      {/* Exercises */}
      {(exercises ?? []).length === 0 ? (
        <div className="card p-6">
          <EmptyState title="还没有添加动作" description="从动作库选择，或按计划开始" />
        </div>
      ) : (
        (exercises ?? []).map((ex) => {
          const info = exerciseById.get(ex.exercise_id);
          const exSets = (setsByExercise.get(ex.id) ?? []).slice().sort((a, b) => a.set_index - b.set_index);
          const nextIndex = (exSets[exSets.length - 1]?.set_index ?? 0) + 1;
          return (
            <div key={ex.id} className="card p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="font-semibold text-gray-900 text-sm">{info?.name ?? ex.exercise_id}</p>
                  {ex.override_reason && (
                    <p className="text-xs text-amber-600">临时替换：{ex.override_reason}</p>
                  )}
                  {info && (
                    <p className="text-xs text-gray-400">
                      {info.metric_type === 'duration' ? '时长型' : '次数型'}
                      {ex.equipment_label ? ` · ${ex.equipment_label}` : ''}
                    </p>
                  )}
                </div>
                <span className="text-xs text-gray-400">{exSets.length} 组</span>
              </div>

              {/* Recorded sets */}
              <ul className="space-y-1.5 mb-3">
                {exSets.map((s) => (
                  <li key={s.id} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2 text-sm">
                    <span className="text-gray-500 text-xs">第{s.set_index}组{s.set_kind === 'warmup' ? '（热身）' : ''}</span>
                    <span className="text-gray-800">
                      {s.status === 'skipped' ? (
                        <span className="text-gray-400">跳过</span>
                      ) : (
                        <>
                          {s.load_kg ? `${s.load_kg}kg` : ''}{' × '}
                          {s.reps !== null ? `${s.reps}次` : s.duration_seconds ? `${s.duration_seconds}秒` : '—'}
                          {s.rir !== null && <span className="text-gray-400 text-xs"> RIR{s.rir}</span>}
                        </>
                      )}
                      {s.pending_sync && <span className="ml-1 text-[10px] text-primary-500">待同步</span>}
                    </span>
                  </li>
                ))}
              </ul>

              {/* Quick log */}
              <SetForm
                metricType={info?.metric_type ?? 'reps'}
                onSubmit={(input, rest) => logSet(ex.id, nextIndex, input, rest)}
                lastLoad={exSets.filter((s) => s.load_kg).slice(-1)[0]?.load_kg ?? null}
              />
            </div>
          );
        })
      )}

      {/* Add exercise */}
      {showAdd ? (
        <div className="card p-4">
          <h3 className="font-semibold text-sm mb-3">添加动作</h3>
          <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto">
            {(catalog ?? []).map((ex) => (
              <button
                key={ex.id}
                onClick={async () => {
                  await workoutActions.addExercise(userId, session.id, ex.id);
                  setShowAdd(false);
                }}
                className="p-3 rounded-xl border border-gray-200 text-left hover:border-primary-300"
              >
                <p className="text-sm font-medium text-gray-800">{ex.name}</p>
                <p className="text-xs text-gray-400">{ex.equipment_tags.join(' / ') || '无器械'}</p>
              </button>
            ))}
            {(catalog ?? []).length === 0 && (
              <p className="text-xs text-gray-400 col-span-2">动作库为空：请先联网同步快照，或由管理员发布动作内容。</p>
            )}
          </div>
          <button onClick={() => setShowAdd(false)} className="mt-3 text-xs text-gray-400">取消</button>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="w-full py-3 rounded-xl border-2 border-dashed border-gray-200 text-sm text-gray-500 flex items-center justify-center gap-2 hover:border-primary-300 hover:text-primary-600"
        >
          <PlusIcon className="w-4 h-4" /> 添加动作
        </button>
      )}

      {/* Discomfort report */}
      <button
        onClick={() => setDiscomfortPrompt(window.prompt('训练中有不适吗？记录后会作为未解决反馈，下次训练前会提醒你（填写"无"可清除）') ?? discomfortPrompt)}
        className="w-full text-xs text-gray-400 py-2"
      >
        {discomfortPrompt ? `不适反馈：${discomfortPrompt}` : '训练中出现不适？点此记录'}
      </button>

      {restSeconds !== null && <RestTimer seconds={restSeconds} onDone={() => setRestSeconds(null)} />}
    </div>
  );
}

function SetForm({
  metricType,
  lastLoad,
  onSubmit,
}: {
  metricType: 'reps' | 'duration';
  lastLoad: string | null;
  onSubmit: (input: {
    load_kg?: string | null; load_mode?: string | null;
    reps?: number | null; duration_seconds?: number | null; rir?: number | null;
    status?: 'completed' | 'skipped';
    discomfort_report?: string | null;
  }, restSeconds?: number) => void;
}) {
  const [load, setLoad] = useState(lastLoad ?? '');
  const [reps, setReps] = useState('');
  const [rir, setRir] = useState('');
  const [skipped, setSkipped] = useState(false);

  const loadMode = 'total_external';

  return (
    <div className="flex items-end gap-2">
      <div className="flex-1">
        <label className="text-[10px] text-gray-400">重量kg</label>
        <input
          type="number" inputMode="decimal" step="0.5" min="0"
          value={load} onChange={(e) => setLoad(e.target.value)}
          placeholder={lastLoad ?? '—'}
          className="input w-full py-1.5 text-sm" disabled={skipped}
        />
      </div>
      <div className="flex-1">
        <label className="text-[10px] text-gray-400">{metricType === 'duration' ? '秒' : '次数'}</label>
        <input
          type="number" inputMode="numeric" min="0"
          value={reps} onChange={(e) => setReps(e.target.value)}
          placeholder="—"
          className="input w-full py-1.5 text-sm" disabled={skipped}
        />
      </div>
      <div className="w-16">
        <label className="text-[10px] text-gray-400">RIR</label>
        <input
          type="number" inputMode="numeric" min="0" max="10"
          value={rir} onChange={(e) => setRir(e.target.value)}
          placeholder="可空"
          className="input w-full py-1.5 text-sm" disabled={skipped}
        />
      </div>
      <button
        onClick={() => {
          if (skipped) {
            onSubmit({ status: 'skipped' });
            return;
          }
          onSubmit(
            {
              load_kg: load || null,
              load_mode: load ? loadMode : null,
              reps: metricType === 'reps' ? (reps ? parseInt(reps, 10) : null) : null,
              duration_seconds: metricType === 'duration' ? (reps ? parseInt(reps, 10) : null) : null,
              rir: rir ? parseInt(rir, 10) : null,
            },
            120,
          );
          setReps('');
          setRir('');
        }}
        className={`px-3 py-2 rounded-lg text-xs font-medium shrink-0 ${
          skipped ? 'bg-gray-100 text-gray-500' : 'btn-primary'
        }`}
      >
        {skipped ? '记为跳过' : <span className="inline-flex items-center gap-1"><FireIcon className="w-3 h-3" />记一组</span>}
      </button>
      <button
        onClick={() => setSkipped(!skipped)}
        className={`px-2 py-2 rounded-lg text-xs shrink-0 ${skipped ? 'text-primary-600 bg-primary-50' : 'text-gray-400'}`}
        title="本组跳过"
      >
        跳过
      </button>
    </div>
  );
}
