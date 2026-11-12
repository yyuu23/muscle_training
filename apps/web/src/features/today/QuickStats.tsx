/**
 * Quick stats — this week's local aggregates.
 *
 * Per plan §7.5: no cross-exercise tonnage in v1; count sessions and
 * recorded working sets instead.
 */

import { CalendarIcon, TrophyIcon, ScaleIcon } from '@heroicons/react/24/outline';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../../offline/database';
import type { LocalWorkoutSession } from '../../offline/types';
import { useAuth } from '../auth/useAuth';

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
    <div className="grid grid-cols-3 gap-3 animate-slide-up">
      <StatCard
        icon={<CalendarIcon className="w-5 h-5" />}
        label="本周训练"
        value={stats?.weekWorkouts ?? 0}
        unit="次"
        color="primary"
      />
      <StatCard
        icon={<TrophyIcon className="w-5 h-5" />}
        label="本周组数"
        value={stats?.weekSets ?? 0}
        unit="组"
        color="success"
      />
      <StatCard
        icon={<ScaleIcon className="w-5 h-5" />}
        label="最近体重"
        value={stats?.latestWeight ? parseFloat(stats.latestWeight) : 0}
        unit={stats?.latestWeight ? 'kg' : ''}
        color="accent"
        empty={stats?.latestWeight ? false : true}
      />
    </div>
  );
}

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  unit: string;
  color: 'primary' | 'success' | 'accent';
  empty?: boolean;
}

function StatCard({ icon, label, value, unit, color, empty }: StatCardProps) {
  const colorClasses = {
    primary: 'bg-primary-50 text-primary-600',
    success: 'bg-green-50 text-green-600',
    accent: 'bg-amber-50 text-amber-600',
  };

  return (
    <div className="card p-4">
      <div className={`w-10 h-10 rounded-xl ${colorClasses[color]} flex items-center justify-center mb-2`}>
        {icon}
      </div>
      <div className="text-2xl font-bold">{empty ? '—' : value}</div>
      <div className="text-xs text-gray-500 mt-0.5">
        {label}
        {!empty && unit && <span className="text-gray-400"> ({unit})</span>}
      </div>
    </div>
  );
}

export type { LocalWorkoutSession };
