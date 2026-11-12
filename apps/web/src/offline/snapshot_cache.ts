/**
 * Snapshot cache (plan §8.6)
 *
 * Refresh triggers: login, foreground, network recovery, manual sync,
 * after outbox upload. Confirmed rows from the server REPLACE local
 * confirmed cache, then pending (unsynced) local records are layered
 * on top — server data never deletes local unsynced events.
 */

import { apiFetch } from '../api/client';
import { db } from './database';

interface SnapshotResponse {
  generated_at: string;
  planning_revision: number;
  profile: {
    version: number;
    goal: string | null;
    height_cm: number | null;
    training_experience_months: number | null;
    sessions_per_week: number | null;
    minutes_per_session: number | null;
    available_weekdays: number[] | null;
    equipment: string[] | null;
    available_load_increments: string[] | null;
  } | null;
  facts: { id: string; kind: string; fact_key: string; value: string; provenance: string }[];
  active_plan: {
    id: string;
    sequence_number: number;
    status: string;
    content: Record<string, unknown>;
    activated_at: string | null;
  } | null;
  exercises: {
    id: string;
    slug: string;
    content_version: number;
    name: string;
    aliases: string[];
    movement_pattern: string | null;
    equipment_tags: string[];
    metric_type: string;
    load_mode: string;
    instructions: string[];
    common_errors: string[];
  }[];
  recent_sessions: Record<string, unknown>[];
  recent_measurements: Record<string, unknown>[];
  recent_meals: Record<string, unknown>[];
}

export async function fetchAndApplySnapshot(ownerUserId: string): Promise<SnapshotResponse> {
  const snapshot = await apiFetch<SnapshotResponse>('/sync/snapshot');

  // Pending local record ids must survive the replace step
  const [pendingSessions, pendingMeasurements, pendingMeals] = await Promise.all([
    db.workoutSessions.where('owner_user_id').equals(ownerUserId)
      .filter((r) => r.pending_sync === true).toArray(),
    db.measurements.where('owner_user_id').equals(ownerUserId)
      .filter((r) => r.pending_sync === true).toArray(),
    db.mealLogs.where('owner_user_id').equals(ownerUserId)
      .filter((r) => r.pending_sync === true).toArray(),
  ]);

  await db.transaction(
    'rw',
    [db.profiles, db.profileFacts, db.plans, db.exercises, db.workoutSessions,
     db.measurements, db.mealLogs, db.syncMetadata],
    async () => {
      // Confirmed cache: replace wholesale
      await db.profiles.where('owner_user_id').equals(ownerUserId).delete();
      await db.profileFacts.where('owner_user_id').equals(ownerUserId).delete();
      await db.plans.where('owner_user_id').equals(ownerUserId).delete();

      if (snapshot.profile) {
        await db.profiles.put({
          id: `profile-${ownerUserId}`,
          owner_user_id: ownerUserId,
          version: snapshot.profile.version,
          goal: snapshot.profile.goal,
          height_cm: snapshot.profile.height_cm,
          training_experience_months: snapshot.profile.training_experience_months,
          sessions_per_week: snapshot.profile.sessions_per_week,
          minutes_per_session: snapshot.profile.minutes_per_session,
          available_weekdays: snapshot.profile.available_weekdays,
          equipment: snapshot.profile.equipment,
          available_load_increments: snapshot.profile.available_load_increments,
        });
      }

      await db.profileFacts.bulkPut(
        snapshot.facts.map((f) => ({
          id: f.id,
          owner_user_id: ownerUserId,
          kind: f.kind,
          fact_key: f.fact_key,
          value: f.value,
          provenance: f.provenance,
        })),
      );

      if (snapshot.active_plan) {
        await db.plans.put({
          id: snapshot.active_plan.id,
          owner_user_id: ownerUserId,
          sequence_number: snapshot.active_plan.sequence_number,
          status: 'active' as const,
          content: snapshot.active_plan.content,
          activated_at: snapshot.active_plan.activated_at,
        });
      }

      // Sessions: replace confirmed, keep pending by re-putting after
      await db.workoutSessions.where('owner_user_id').equals(ownerUserId).delete();
      await db.workoutSessions.bulkPut(
        snapshot.recent_sessions.map((s) => ({
          id: s.id as string,
          owner_user_id: ownerUserId,
          plan_version_id: (s.plan_version_id as string) ?? null,
          plan_day_key: (s.plan_day_key as string) ?? null,
          started_at: s.started_at as string,
          completed_at: (s.completed_at as string) ?? null,
          status: s.status as 'in_progress' | 'completed' | 'abandoned',
          precheck: null,
          notes: null,
          version: s.version as number,
        })),
      );
      await db.workoutSessions.bulkPut(pendingSessions);

      await db.measurements.where('owner_user_id').equals(ownerUserId).delete();
      await db.measurements.bulkPut(
        snapshot.recent_measurements.map((m) => ({
          id: m.id as string,
          owner_user_id: ownerUserId,
          measurement_type: m.measurement_type as 'weight',
          value: m.value as string,
          unit: m.unit as string,
          observed_at: m.observed_at as string,
          source: 'user_logged',
          notes: null,
          version: m.version as number,
        })),
      );
      await db.measurements.bulkPut(pendingMeasurements);

      await db.mealLogs.where('owner_user_id').equals(ownerUserId).delete();
      await db.mealLogs.bulkPut(
        snapshot.recent_meals.map((x) => ({
          id: x.id as string,
          owner_user_id: ownerUserId,
          occurred_at: x.occurred_at as string,
          meal_type: (x.meal_type as string) ?? null,
          description: x.description as string,
          items: (x.items as unknown[]) ?? null,
          nutrition: (x.nutrition as Record<string, unknown>) ?? null,
          nutrition_source: (x.nutrition_source as 'unknown') ?? 'unknown',
          version: x.version as number,
        })),
      );
      await db.mealLogs.bulkPut(pendingMeals);

      // Exercise cards (offline viewing of instructions)
      await db.exercises.clear();
      await db.exercises.bulkPut(
        snapshot.exercises.map((e) => ({
          id: e.id,
          slug: e.slug,
          content_version: e.content_version,
          name: e.name,
          aliases: e.aliases ?? [],
          movement_pattern: e.movement_pattern,
          equipment_tags: e.equipment_tags ?? [],
          metric_type: (e.metric_type as 'reps' | 'duration') ?? 'reps',
          load_mode: e.load_mode,
          instructions: e.instructions ?? [],
          common_errors: e.common_errors ?? [],
        })),
      );

      await db.syncMetadata.put({
        key: 'last_snapshot',
        value: snapshot.generated_at,
        updated_at: new Date().toISOString(),
      });
      await db.syncMetadata.put({
        key: 'planning_revision',
        value: String(snapshot.planning_revision),
        updated_at: new Date().toISOString(),
      });
    },
  );

  return snapshot;
}

/** Planning revision as of the last snapshot (plan basis guard). */
export async function cachedPlanningRevision(): Promise<number | null> {
  const record = await db.syncMetadata.get('planning_revision');
  return record ? parseInt(record.value, 10) : null;
}
