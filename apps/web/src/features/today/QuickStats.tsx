/**
 * Quick stats — this week's local aggregates (animated count-up).
 *
 * Per plan §7.5: no cross-exercise tonnage in v1; count sessions and
 * recorded working sets instead.
 */

import { CalendarIcon, TrophyIcon, ScaleIcon } from '@heroicons/react/24/outline';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../../offline/database';
import type { LocalWorkoutSession } from '../../offline/types';
import { useAuth } from '../auth/useAuth';
import { StatCard } from '../../components/ui/Card';

export function QuickStats() {
  const { user } = useAuth();

  const stats = useLiveQuery(
    async () => {
      if (!user) return { weekWorkouts: 0, weekSets: 0, latestWeight: null as string | null };
      const cutoff = new Date(Date.now() - 7 * 24 * 3600 * 1000).toISOString();

      const sessions = await db.workoutSessions
        .where('owner_user_id')
        .equals(user.id)
        .and((s) => s.started_at >= cutoff)
        .toArray();

      const exerciseIds = sessions.length
        ? (await db.sessionExercises.where('session_id').anyOf(sessions.map((s) => s.id)).toArray()).map((e) => e.id)
        : [];
      const setCount = exerciseIds.length
        ? await db.workoutSets.where('session_exercise_id').anyOf(exerciseIds).count()
        : 0;

      const weight = await db.measurements
        .where('owner_user_id')
        .equals(user.id)
        .and((m) => m.measurement_type === 'weight')
        .reverse()
        .sortBy('observed_at');

      return {
        weekWorkouts: sessions.filter((s) => s.status === 'completed').length,
        weekSets: setCount,
        latestWeight: weight[0]?.value ?? null,
      };
    },
    [user?.id],
  );

  return (
    <div className="grid grid-cols-3 lg:grid-cols-1 gap-3">
      <StatCard
        icon={<CalendarIcon className="w-5 h-5" />}
        label="本周训练"
        value={stats?.weekWorkouts ?? 0}
        unit="次"
        tone="primary"
        index={0}
      />
      <StatCard
        icon={<TrophyIcon className="w-5 h-5" />}
        label="本周组数"
        value={stats?.weekSets ?? 0}
        unit="组"
        tone="success"
        index={1}
      />
      <StatCard
        icon={<ScaleIcon className="w-5 h-5" />}
        label="最近体重"
        value={stats?.latestWeight ? parseFloat(stats.latestWeight) : 0}
        unit={stats?.latestWeight ? 'kg' : ''}
        tone="warning"
        empty={!stats?.latestWeight}
        index={2}
      />
    </div>
  );
}

export type { LocalWorkoutSession };
