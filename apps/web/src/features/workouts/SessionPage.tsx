/**
 * Session page (plan §8.1 训练记录页): per-set logging with load/reps/
 * RIR, rest timer (ring countdown), temporary substitution, completion
 * with celebration. Offline-first: every write is local + outbox.
 *
 * High-frequency interactions (记一组) get instant feedback only — no
 * delay-inducing animations.
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useLiveQuery } from 'dexie-react-hooks';
import {
  CheckIcon, PlusIcon, FireIcon, SparklesIcon, XMarkIcon,
} from '@heroicons/react/24/solid';
import { db } from '../../offline/database';
import { workoutActions, useWorkoutSession } from './useWorkoutSession';
import { useAuth } from '../auth/useAuth';
import { EmptyState } from '../../components/ErrorState';
import { useSyncStatus } from '../../hooks/useSync';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { ProgressRing } from '../../components/ui/ProgressRing';
import { Sheet } from '../../components/ui/Sheet';
import { Confetti } from '../../components/ui/Confetti';
import { useToast } from '../../components/ui/Toast';

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

  return (
    <div className="fixed bottom-24 lg:bottom-8 left-1/2 -translate-x-1/2 z-40 animate-scale-in">
      <div className="bg-surface border border-border-default shadow-strong rounded-3xl px-5 py-3 flex items-center gap-3">
        <ProgressRing total={seconds} remaining={remaining} size={56} />
        <div>
          <p className="text-sm font-semibold text-text">休息中</p>
          <p className="text-xs text-text-muted">恢复呼吸，准备下一组</p>
        </div>
      </div>
    </div>
  );
}

export function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { status, pendingCount } = useSyncStatus(user?.id ?? null);
  const toast = useToast();
  const userId = user?.id ?? '';

  const { session, exercises, sets } = useWorkoutSession(id ?? null);
  const catalog = useLiveQuery(() => db.exercises.toArray(), []);

  const [restSeconds, setRestSeconds] = useState<number | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [discomfortOpen, setDiscomfortOpen] = useState(false);
  const [discomfortText, setDiscomfortText] = useState('');
  const [discomfortSaved, setDiscomfortSaved] = useState<string | null>(null);
  const [celebrate, setCelebrate] = useState(0);

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
      <div className="page-container py-10">
        <EmptyState title="训练不存在" action={
          <Button size="sm" onClick={() => navigate('/today')}>返回今日</Button>
        } />
      </div>
    );
  }

  if (session.status !== 'in_progress') {
    return (
      <div className="page-container py-10 space-y-4">
        <Confetti trigger={celebrate} />
        <div className="card p-8 text-center animate-scale-in">
          <span className="inline-flex w-16 h-16 rounded-3xl bg-success-soft text-success items-center justify-center mb-3">
            <CheckIcon className="w-8 h-8" />
          </span>
          <p className="font-semibold text-lg text-text">训练已完成</p>
          <p className="text-sm text-text-secondary mt-1.5">
            {new Date(session.started_at).toLocaleString('zh-CN')} · 共 {(sets ?? []).length} 组
          </p>
          <p className="text-xs text-text-muted mt-3 flex items-center justify-center gap-1">
            <SparklesIcon className="w-3.5 h-3.5" /> 干得漂亮，继续保持
          </p>
        </div>
        <Button className="w-full py-3" onClick={() => navigate('/history')}>
          查看历史记录
        </Button>
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
    toast.show(input.status === 'skipped' ? '已记为跳过' : '已记录 1 组');
    if (restSeconds && input.status !== 'skipped') setRestSeconds(restSeconds);
  };

  const completeWorkout = async () => {
    await workoutActions.complete(userId, session.id, discomfortSaved);
    setCelebrate((c) => c + 1);
    toast.show('训练完成，辛苦了！', 'success');
    window.setTimeout(() => navigate('/today'), 900);
  };

  return (
    <div className="page-container py-5 pb-28 lg:pb-10 space-y-4">
      <Confetti trigger={celebrate} />
      <div className="flex items-center justify-between animate-fade-in">
        <div>
          <h1 className="text-xl font-bold text-text">训练中</h1>
          <p className="text-xs text-text-muted mt-0.5">
            {new Date(session.started_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })} 开始
            {status === 'offline' ? ' · 离线记录中' : pendingCount > 0 ? ` · ${pendingCount} 条待同步` : ''}
          </p>
        </div>
        <Button size="sm" onClick={completeWorkout}>
          <CheckIcon className="w-4 h-4" /> 完成训练
        </Button>
      </div>

      {/* Exercises */}
      {(exercises ?? []).length === 0 ? (
        <div className="card p-6">
          <EmptyState title="还没有添加动作" description="从动作库选择，或按计划开始" />
        </div>
      ) : (
        <div className="space-y-4 lg:grid lg:grid-cols-2 lg:gap-4 lg:space-y-0">
        {(exercises ?? []).map((ex, exIdx) => {
          const info = exerciseById.get(ex.exercise_id);
          const exSets = (setsByExercise.get(ex.id) ?? []).slice().sort((a, b) => a.set_index - b.set_index);
          const nextIndex = (exSets[exSets.length - 1]?.set_index ?? 0) + 1;
          return (
            <div
              key={ex.id}
              className="card card-solid p-4 animate-slide-up"
              style={{ animationDelay: `${exIdx * 60}ms` }}
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="font-semibold text-text text-sm">{info?.name ?? ex.exercise_id}</p>
                  {ex.override_reason && (
                    <p className="text-xs text-warning mt-0.5">临时替换：{ex.override_reason}</p>
                  )}
                  {info && (
                    <p className="text-xs text-text-muted mt-0.5">
                      {info.metric_type === 'duration' ? '时长型' : '次数型'}
                      {ex.equipment_label ? ` · ${ex.equipment_label}` : ''}
                    </p>
                  )}
                </div>
                <Badge tone="primary">{exSets.length} 组</Badge>
              </div>

              {/* Recorded sets */}
              <ul className="space-y-1.5 mb-3">
                {exSets.map((s, i) => (
                  <li
                    key={s.id}
                    className="flex items-center justify-between bg-surface-2 rounded-xl px-3 py-2 text-sm animate-slide-up"
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <span className="text-text-muted text-xs">
                      第{s.set_index}组{s.set_kind === 'warmup' ? '（热身）' : ''}
                    </span>
                    <span className="text-text tabular-nums">
                      {s.status === 'skipped' ? (
                        <span className="text-text-muted">跳过</span>
                      ) : (
                        <>
                          {s.load_kg ? `${s.load_kg}kg` : ''}{' × '}
                          {s.reps !== null ? `${s.reps}次` : s.duration_seconds ? `${s.duration_seconds}秒` : '—'}
                          {s.rir !== null && <span className="text-text-muted text-xs"> RIR{s.rir}</span>}
                        </>
                      )}
                      {s.pending_sync && <Badge tone="primary" className="ml-1.5 !text-[10px] !px-1.5 !py-0">待同步</Badge>}
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
        }
        </div>
      )}

      {/* Add exercise */}
      {showAdd ? (
        <div className="card card-solid p-4 animate-scale-in">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-sm">添加动作</h3>
            <button onClick={() => setShowAdd(false)} className="p-1 rounded-lg text-text-muted hover:text-text">
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto scrollbar-thin">
            {(catalog ?? []).map((ex, i) => (
              <button
                key={ex.id}
                onClick={async () => {
                  await workoutActions.addExercise(userId, session.id, ex.id);
                  toast.show(`已添加 ${ex.name}`);
                  setShowAdd(false);
                }}
                className="p-3 rounded-xl border border-border-default bg-surface text-left hover:border-primary hover:shadow-soft transition-all animate-fade-in"
                style={{ animationDelay: `${i * 30}ms` }}
              >
                <p className="text-sm font-medium text-text">{ex.name}</p>
                <p className="text-xs text-text-muted mt-0.5">{ex.equipment_tags.join(' / ') || '无器械'}</p>
              </button>
            ))}
            {(catalog ?? []).length === 0 && (
              <p className="text-xs text-text-muted col-span-2 py-4 text-center">
                动作库为空：请先联网同步快照，或由管理员发布动作内容。
              </p>
            )}
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="w-full py-3.5 rounded-2xl border-2 border-dashed border-border-strong text-sm text-text-muted flex items-center justify-center gap-2 hover:border-primary hover:text-primary transition-colors"
        >
          <PlusIcon className="w-4 h-4" /> 添加动作
        </button>
      )}

      {/* Discomfort report — proper sheet instead of window.prompt */}
      <button
        onClick={() => setDiscomfortOpen(true)}
        className="w-full text-xs text-text-muted py-2 hover:text-text-secondary transition-colors"
      >
        {discomfortSaved ? `不适反馈：${discomfortSaved}（点击修改）` : '训练中出现不适？点此记录'}
      </button>

      <Sheet open={discomfortOpen} onClose={() => setDiscomfortOpen(false)} title="记录不适反馈">
        <p className="text-sm text-text-secondary leading-relaxed mb-3">
          记录后会作为未解决反馈，下次训练前会提醒你再次确认。填写「无」可清除记录。
        </p>
        <textarea
          className="input min-h-24"
          placeholder="例如：左肩推举时有轻微不适"
          value={discomfortText}
          onChange={(e) => setDiscomfortText(e.target.value)}
        />
        <div className="flex gap-2 mt-4">
          <Button
            className="flex-1"
            onClick={() => {
              setDiscomfortSaved(discomfortText.trim() || null);
              setDiscomfortOpen(false);
              if (discomfortText.trim()) toast.show('已记录不适反馈');
            }}
          >
            保存
          </Button>
          <Button variant="secondary" className="flex-1" onClick={() => setDiscomfortOpen(false)}>
            取消
          </Button>
        </div>
      </Sheet>

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
        <label className="text-[10px] font-medium text-text-muted uppercase tracking-wide">重量kg</label>
        <input
          type="number" inputMode="decimal" step="0.5" min="0"
          value={load} onChange={(e) => setLoad(e.target.value)}
          placeholder={lastLoad ?? '—'}
          className="input !py-2 text-sm tabular-nums mt-0.5" disabled={skipped}
        />
      </div>
      <div className="flex-1">
        <label className="text-[10px] font-medium text-text-muted uppercase tracking-wide">
          {metricType === 'duration' ? '秒' : '次数'}
        </label>
        <input
          type="number" inputMode="numeric" min="0"
          value={reps} onChange={(e) => setReps(e.target.value)}
          placeholder="—"
          className="input !py-2 text-sm tabular-nums mt-0.5" disabled={skipped}
        />
      </div>
      <div className="w-16">
        <label className="text-[10px] font-medium text-text-muted uppercase tracking-wide">RIR</label>
        <input
          type="number" inputMode="numeric" min="0" max="10"
          value={rir} onChange={(e) => setRir(e.target.value)}
          placeholder="可空"
          className="input !py-2 text-sm tabular-nums mt-0.5" disabled={skipped}
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
        className={`btn shrink-0 !px-3.5 !py-2.5 text-xs ${skipped ? 'btn-secondary' : 'btn-primary'}`}
      >
        {skipped ? '记为跳过' : <span className="inline-flex items-center gap-1"><FireIcon className="w-3.5 h-3.5" />记一组</span>}
      </button>
      <button
        onClick={() => setSkipped(!skipped)}
        className={`btn btn-ghost !px-2.5 !py-2.5 text-xs shrink-0 ${skipped ? '!text-primary !bg-primary-soft' : ''}`}
        title="本组跳过"
      >
        跳过
      </button>
    </div>
  );
}
