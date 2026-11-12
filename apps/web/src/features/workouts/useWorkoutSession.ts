/**
 * Workout session hooks — single offline-first write path (plan §6.3)
 *
 * All writes: local Dexie + outbox event. Online and offline share
 * exactly this path; the sync engine uploads later.
 */

import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../../offline/database';
import { outboxService } from '../../offline/outbox';

export function useWorkoutSession(sessionId: string | null) {
  const session = useLiveQuery(
    async () => (sessionId ? db.workoutSessions.get(sessionId) : undefined),
    [sessionId],
  );

  const exercises = useLiveQuery(
    async () => {
      if (!sessionId) return [];
      return db.sessionExercises
        .where('session_id')
        .equals(sessionId)
        .sortBy('position');
    },
    [sessionId],
  );

  const sets = useLiveQuery(
    async () => {
      if (!sessionId || exercises === undefined) return [];
      const ids = exercises.map((e) => e.id);
      return db.workoutSets
        .where('session_exercise_id')
        .anyOf(ids)
        .sortBy('set_index');
    },
    [sessionId, exercises],
  );

  return { session, exercises, sets };
}

export function useActiveSession(userId: string | null) {
  return useLiveQuery(
    async () => {
      if (!userId) return null;
      const sessions = await db.workoutSessions
        .where('owner_user_id')
        .equals(userId)
        .and((s) => s.status === 'in_progress')
        .reverse()
        .sortBy('started_at');
      return sessions[0] ?? null;
    },
    [userId],
  );
}

export const workoutActions = {
  start: (userId: string, opts?: { plan_version_id?: string | null; plan_day_key?: string | null; precheck?: Record<string, unknown> | null }) =>
    outboxService.workoutStarted(userId, {
      id: crypto.randomUUID(),
      plan_version_id: opts?.plan_version_id ?? null,
      plan_day_key: opts?.plan_day_key ?? null,
      started_at: new Date().toISOString(),
      precheck: opts?.precheck ?? null,
    }),

  addExercise: (
    userId: string,
    sessionId: string,
    exerciseId: string,
    opts?: { equipment_label?: string | null; override_reason?: string | null },
  ) =>
    outboxService.sessionExerciseAdded(userId, {
      id: crypto.randomUUID(),
      session_id: sessionId,
      exercise_id: exerciseId,
      position: Date.now(), // stable enough ordering for UI
      equipment_label: opts?.equipment_label ?? null,
      override_reason: opts?.override_reason ?? null,
    }),

  logSet: (
    userId: string,
    sessionExerciseId: string,
    input: {
      set_index: number;
      set_kind?: 'warmup' | 'work';
      status?: 'completed' | 'skipped' | 'failed';
      load_kg?: string | null;
      load_mode?: string | null;
      reps?: number | null;
      duration_seconds?: number | null;
      rir?: number | null;
      discomfort_report?: string | null;
    },
  ) =>
    outboxService.setLogged(userId, {
      id: crypto.randomUUID(),
      session_exercise_id: sessionExerciseId,
      set_index: input.set_index,
      set_kind: input.set_kind ?? 'work',
      status: input.status ?? 'completed',
      load_kg: input.load_kg ?? null,
      load_mode: input.load_mode ?? null,
      reps: input.reps ?? null,
      duration_seconds: input.duration_seconds ?? null,
      rir: input.rir ?? null,
      discomfort_report: input.discomfort_report ?? null,
      performed_at: new Date().toISOString(),
    }),

  complete: (userId: string, sessionId: string, notes?: string | null) =>
    outboxService.workoutCompleted(userId, {
      session_id: sessionId,
      completed_at: new Date().toISOString(),
      notes: notes ?? null,
    }),
};
