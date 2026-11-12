/**
 * Active session card: live duration + recorded counts from Dexie.
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLiveQuery } from 'dexie-react-hooks';
import { ClockIcon, FireIcon } from '@heroicons/react/24/outline';
import { db } from '../../offline/database';
import type { LocalWorkoutSession } from '../../offline/types';
import { formatDuration } from '../../utils/format';

export function ActiveSessionCard({ session }: { session: LocalWorkoutSession }) {
  const navigate = useNavigate();
  const [duration, setDuration] = useState(0);

  const exercises = useLiveQuery(
    () => db.sessionExercises.where('session_id').equals(session.id).count(),
    [session.id],
  );
  const sets = useLiveQuery(async () => {
    const exerciseRows = await db.sessionExercises.where('session_id').equals(session.id).toArray();
    if (exerciseRows.length === 0) return 0;
    return db.workoutSets
      .where('session_exercise_id')
      .anyOf(exerciseRows.map((e) => e.id))
      .count();
  }, [session.id]);

  useEffect(() => {
    const startTime = new Date(session.started_at).getTime();
    const updateDuration = () => setDuration(Date.now() - startTime);
    updateDuration();
    const timer = setInterval(updateDuration, 1000);
    return () => clearInterval(timer);
  }, [session.started_at]);

  return (
    <div className="card-interactive bg-gradient-to-br from-accent-500 to-accent-600 text-white animate-scale-in">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <FireIcon className="w-5 h-5 animate-pulse" />
            <span className="text-sm font-medium opacity-90">训练进行中</span>
          </div>
          <h3 className="text-xl font-bold">继续训练</h3>
        </div>
        <div className="badge bg-white/20 text-white border-white/30">
          <ClockIcon className="w-4 h-4 mr-1" />
          {formatDuration(duration)}
        </div>
      </div>

      <div className="flex gap-4 text-sm mb-4">
        <div>
          <div className="opacity-75">动作</div>
          <div className="text-lg font-bold">{exercises ?? 0}</div>
        </div>
        <div>
          <div className="opacity-75">组数</div>
          <div className="text-lg font-bold">{sets ?? 0}</div>
        </div>
        {session.pending_sync && (
          <div>
            <div className="opacity-75">状态</div>
            <div className="text-sm font-bold mt-1">待同步</div>
          </div>
        )}
      </div>

      <button
        onClick={() => navigate(`/workouts/${session.id}`)}
        className="w-full bg-white text-accent-600 font-semibold py-3 rounded-xl hover:bg-gray-50 transition-colors"
      >
        继续训练
      </button>
    </div>
  );
}
