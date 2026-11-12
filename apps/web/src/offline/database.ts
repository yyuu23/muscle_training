/**
 * IndexedDB database (Dexie) — plan §8.3
 *
 * All user-data records carry owner_user_id (account boundary).
 * v2 adds session exercises, sets, facts, form drafts and the
 * full outbox shape (event_id/device_id/sequence/hash/backoff).
 */

import Dexie, { type EntityTable } from 'dexie';
import type {
  FormDraft,
  LocalExercise,
  LocalMealLog,
  LocalMeasurement,
  LocalPlan,
  LocalProfile,
  LocalProfileFact,
  LocalSessionExercise,
  LocalWorkoutSession,
  LocalWorkoutSet,
  OutboxEvent,
  SyncMetadataRecord,
} from './types';

class MuscleTrainingDatabase extends Dexie {
  profiles!: EntityTable<LocalProfile, 'id'>;
  profileFacts!: EntityTable<LocalProfileFact, 'id'>;
  plans!: EntityTable<LocalPlan, 'id'>;
  exercises!: EntityTable<LocalExercise, 'id'>;
  workoutSessions!: EntityTable<LocalWorkoutSession, 'id'>;
  sessionExercises!: EntityTable<LocalSessionExercise, 'id'>;
  workoutSets!: EntityTable<LocalWorkoutSet, 'id'>;
  measurements!: EntityTable<LocalMeasurement, 'id'>;
  mealLogs!: EntityTable<LocalMealLog, 'id'>;
  outbox!: EntityTable<OutboxEvent, 'id'>;
  syncMetadata!: EntityTable<SyncMetadataRecord, 'key'>;
  formDrafts!: EntityTable<FormDraft, 'key'>;

  constructor() {
    super('muscle_training_v2');

    // v1 (legacy shape kept so upgrades from the old build don't throw)
    this.version(1).stores({
      profiles: 'id, user_id, updated_at',
      plans: 'id, user_id, status, created_at',
      sessions: 'id, user_id, started_at, status, created_at',
      exercises: 'id, slug, name',
      measurements: 'id, user_id, observed_at, type, created_at',
      meals: 'id, user_id, occurred_at, meal_type, created_at',
      outbox: '++id, user_id, event_type, status, created_at, idempotency_key',
      sync_metadata: 'key, updated_at',
    });

    // v2 — plan-aligned shape
    this.version(2).stores({
      profiles: 'id, owner_user_id',
      profileFacts: 'id, owner_user_id, kind',
      plans: 'id, owner_user_id, status, sequence_number',
      exercises: 'id, slug, name',
      workoutSessions: 'id, owner_user_id, started_at, status',
      sessionExercises: 'id, owner_user_id, session_id, position',
      workoutSets: 'id, owner_user_id, session_exercise_id, set_index',
      measurements: 'id, owner_user_id, observed_at, measurement_type',
      mealLogs: 'id, owner_user_id, occurred_at, meal_type',
      outbox: '++id, event_id, owner_user_id, event_type, status, next_attempt_at, client_sequence',
      syncMetadata: 'key, updated_at',
      formDrafts: 'key, owner_user_id, updated_at',
    }).upgrade((tx) => {
      // Legacy v1 tables are dropped by Dexie when not declared in v2
      void tx;
    });
  }

  /** Clear a single user's confirmed cache + outbox (account switch). */
  async clearUserData(ownerUserId: string): Promise<void> {
    await this.transaction(
      'rw',
      [this.profiles, this.profileFacts, this.plans, this.workoutSessions, this.sessionExercises,
       this.workoutSets, this.measurements, this.mealLogs, this.outbox, this.syncMetadata, this.formDrafts],
      async () => {
        await Promise.all([
          this.profiles.where('owner_user_id').equals(ownerUserId).delete(),
          this.profileFacts.where('owner_user_id').equals(ownerUserId).delete(),
          this.plans.where('owner_user_id').equals(ownerUserId).delete(),
          this.workoutSessions.where('owner_user_id').equals(ownerUserId).delete(),
          this.sessionExercises.where('owner_user_id').equals(ownerUserId).delete(),
          this.workoutSets.where('owner_user_id').equals(ownerUserId).delete(),
          this.measurements.where('owner_user_id').equals(ownerUserId).delete(),
          this.mealLogs.where('owner_user_id').equals(ownerUserId).delete(),
          this.outbox.where('owner_user_id').equals(ownerUserId).delete(),
          this.syncMetadata.clear(),
          this.formDrafts.where('owner_user_id').equals(ownerUserId).delete(),
        ]);
      },
    );
  }

  async getStorageUsage(): Promise<{ usage: number; quota: number }> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      return { usage: estimate.usage || 0, quota: estimate.quota || 0 };
    }
    return { usage: 0, quota: 0 };
  }

  /** Keep ~30 days of confirmed records (plan §8.2), never pending ones. */
  async cleanupOldData(ownerUserId: string): Promise<number> {
    const cutoff = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString();
    let deleted = 0;

    const cleanIfNotPending = async (
      table: EntityTable<{ id: string; pending_sync?: boolean }, 'id'>,
      timeField: 'started_at' | 'observed_at' | 'occurred_at',
    ) => {
      const rows = await table
        .where('owner_user_id').equals(ownerUserId)
        .and((row) => (row as Record<string, unknown>)[timeField] as string < cutoff && !row.pending_sync)
        .toArray();
      deleted += rows.length;
      await table.bulkDelete(rows.map((r) => r.id));
    };

    await cleanIfNotPending(this.workoutSessions as never, 'started_at');
    await cleanIfNotPending(this.measurements as never, 'observed_at');
    await cleanIfNotPending(this.mealLogs as never, 'occurred_at');
    return deleted;
  }
}

export const db = new MuscleTrainingDatabase();
export { MuscleTrainingDatabase };
