/**
 * Outbox (plan §8.3 / §8.5)
 *
 * Every recording action writes local Dexie rows AND enqueues a sync
 * event — online and offline share this single write path.
 * Payload freezes after creation; event ids are client UUIDs reused
 * verbatim on retry.
 */

import { db } from './database';
import type { OutboxEvent, OutboxEventType } from './types';

const DEVICE_ID_KEY = 'device_id';

export function getDeviceId(): string {
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  if (!deviceId) {
    deviceId = crypto.randomUUID();
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
  }
  return deviceId;
}

async function sha256Hex(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/** Stable canonical JSON for hashing (sorted keys). */
function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .filter(([, v]) => v !== undefined)
    .sort(([a], [b]) => (a < b ? -1 : 1));
  return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${canonicalJson(v)}`).join(',')}}`;
}

async function nextClientSequence(ownerUserId: string): Promise<number> {
  const record = await db.syncMetadata.get('client_sequence');
  const next = record ? parseInt(record.value, 10) + 1 : 1;
  await db.syncMetadata.put({
    key: 'client_sequence',
    value: String(next),
    updated_at: new Date().toISOString(),
  });
  void ownerUserId;
  return next;
}

class OutboxService {
  private async enqueue(
    ownerUserId: string,
    eventType: OutboxEventType,
    payload: Record<string, unknown>,
  ): Promise<void> {
    const event: OutboxEvent = {
      event_id: crypto.randomUUID(),
      owner_user_id: ownerUserId,
      device_id: getDeviceId(),
      client_sequence: await nextClientSequence(ownerUserId),
      event_type: eventType,
      payload,
      payload_hash: await sha256Hex(canonicalJson({ event_type: eventType, payload })),
      status: 'pending',
      first_attempt_at: null,
      attempt_count: 0,
      next_attempt_at: new Date().toISOString(),
      last_error: null,
      created_at: new Date().toISOString(),
    };
    await db.outbox.add(event);
  }

  /** Start a workout (also writes the local session row). */
  async workoutStarted(ownerUserId: string, p: {
    id: string;
    plan_version_id?: string | null;
    plan_day_key?: string | null;
    started_at: string;
    precheck?: Record<string, unknown> | null;
    notes?: string | null;
  }): Promise<void> {
    await db.workoutSessions.put({
      id: p.id,
      owner_user_id: ownerUserId,
      plan_version_id: p.plan_version_id ?? null,
      plan_day_key: p.plan_day_key ?? null,
      started_at: p.started_at,
      completed_at: null,
      status: 'in_progress',
      precheck: p.precheck ?? null,
      notes: p.notes ?? null,
      version: 1,
      pending_sync: true,
    });
    await this.enqueue(ownerUserId, 'workout.started', {
      id: p.id,
      plan_version_id: p.plan_version_id ?? null,
      plan_day_key: p.plan_day_key ?? null,
      started_at: p.started_at,
      precheck: p.precheck ?? null,
      client_created_at: new Date().toISOString(),
    });
  }

  async sessionExerciseAdded(ownerUserId: string, p: {
    id: string;
    session_id: string;
    exercise_id: string;
    plan_item_id?: string | null;
    position: number;
    equipment_label?: string | null;
    override_reason?: string | null;
  }): Promise<void> {
    await db.sessionExercises.put({
      id: p.id,
      owner_user_id: ownerUserId,
      session_id: p.session_id,
      exercise_id: p.exercise_id,
      plan_item_id: p.plan_item_id ?? null,
      position: p.position,
      equipment_label: p.equipment_label ?? null,
      override_reason: p.override_reason ?? null,
      completion_status: 'not_recorded',
      version: 1,
      pending_sync: true,
    });
    await this.enqueue(ownerUserId, 'session_exercise.added', {
      id: p.id,
      session_id: p.session_id,
      exercise_id: p.exercise_id,
      plan_item_id: p.plan_item_id ?? null,
      position: p.position,
      equipment_label: p.equipment_label ?? null,
      override_reason: p.override_reason ?? null,
      client_created_at: new Date().toISOString(),
    });
  }

  async setLogged(ownerUserId: string, p: {
    id: string;
    session_exercise_id: string;
    set_index: number;
    set_kind: 'warmup' | 'work';
    status: 'completed' | 'skipped' | 'failed';
    load_kg?: string | null;
    load_mode?: string | null;
    reps?: number | null;
    duration_seconds?: number | null;
    rir?: number | null;
    discomfort_report?: string | null;
    performed_at: string;
  }): Promise<void> {
    await db.workoutSets.put({
      id: p.id,
      owner_user_id: ownerUserId,
      session_exercise_id: p.session_exercise_id,
      set_index: p.set_index,
      set_kind: p.set_kind,
      status: p.status,
      load_kg: p.load_kg ?? null,
      load_mode: p.load_mode ?? null,
      reps: p.reps ?? null,
      duration_seconds: p.duration_seconds ?? null,
      rir: p.rir ?? null,
      discomfort_report: p.discomfort_report ?? null,
      performed_at: p.performed_at,
      version: 1,
      pending_sync: true,
    });
    await this.enqueue(ownerUserId, 'set.logged', {
      id: p.id,
      session_exercise_id: p.session_exercise_id,
      set_index: p.set_index,
      set_kind: p.set_kind,
      status: p.status,
      load_kg: p.load_kg ?? null,
      load_mode: p.load_mode ?? null,
      reps: p.reps ?? null,
      duration_seconds: p.duration_seconds ?? null,
      rir: p.rir ?? null,
      discomfort_report: p.discomfort_report ?? null,
      performed_at: p.performed_at,
      client_created_at: new Date().toISOString(),
    });
  }

  async workoutCompleted(ownerUserId: string, p: {
    session_id: string;
    completed_at: string;
    notes?: string | null;
  }): Promise<void> {
    await db.workoutSessions.update(p.session_id, {
      completed_at: p.completed_at,
      status: 'completed',
      notes: p.notes ?? null,
      pending_sync: true,
    });
    await this.enqueue(ownerUserId, 'workout.completed', {
      session_id: p.session_id,
      completed_at: p.completed_at,
      notes: p.notes ?? null,
      client_created_at: new Date().toISOString(),
    });
  }

  async measurementCreated(ownerUserId: string, p: {
    id: string;
    measurement_type: 'weight' | 'body_fat_percentage' | 'circumference' | 'other';
    value: string;
    unit: string;
    observed_at: string;
    notes?: string | null;
  }): Promise<void> {
    await db.measurements.put({
      id: p.id,
      owner_user_id: ownerUserId,
      measurement_type: p.measurement_type,
      value: p.value,
      unit: p.unit,
      observed_at: p.observed_at,
      source: 'user_logged',
      notes: p.notes ?? null,
      version: 1,
      pending_sync: true,
    });
    await this.enqueue(ownerUserId, 'measurement.created', {
      id: p.id,
      measurement_type: p.measurement_type,
      value: p.value,
      unit: p.unit,
      observed_at: p.observed_at,
      notes: p.notes ?? null,
      client_created_at: new Date().toISOString(),
    });
  }

  async mealCreated(ownerUserId: string, p: {
    id: string;
    occurred_at: string;
    meal_type?: 'breakfast' | 'lunch' | 'dinner' | 'snack' | 'other' | null;
    description: string;
    items?: unknown[] | null;
    nutrition?: Record<string, unknown> | null;
    nutrition_source: 'user_label' | 'user_estimate' | 'model_estimate' | 'unknown';
  }): Promise<void> {
    await db.mealLogs.put({
      id: p.id,
      owner_user_id: ownerUserId,
      occurred_at: p.occurred_at,
      meal_type: p.meal_type ?? null,
      description: p.description,
      items: p.items ?? null,
      nutrition: p.nutrition ?? null,
      nutrition_source: p.nutrition_source,
      version: 1,
      pending_sync: true,
    });
    await this.enqueue(ownerUserId, 'meal.created', {
      id: p.id,
      occurred_at: p.occurred_at,
      meal_type: p.meal_type ?? null,
      description: p.description,
      items: p.items ?? null,
      nutrition: p.nutrition ?? null,
      nutrition_source: p.nutrition_source,
      client_created_at: new Date().toISOString(),
    });
  }

  // --- Queries used by UI ------------------------------------------------

  async getPendingCount(ownerUserId: string): Promise<number> {
    return db.outbox
      .where('owner_user_id')
      .equals(ownerUserId)
      .filter((e) => e.status === 'pending' || e.status === 'sending')
      .count();
  }

  async getNeedsAttention(ownerUserId: string): Promise<OutboxEvent[]> {
    return db.outbox
      .where('owner_user_id')
      .equals(ownerUserId)
      .and((e) => e.status === 'needs_attention')
      .toArray();
  }

  /** On startup: restore stuck `sending` back to pending (plan §8.5). */
  async restoreStuckSending(): Promise<number> {
    const stuck = await db.outbox.where('status').equals('sending').toArray();
    await Promise.all(
      stuck.map((e) => db.outbox.update(e.id!, { status: 'pending' as const })),
    );
    return stuck.length;
  }

  /** Mark a local record as synced once its event is acknowledged. */
  async acknowledge(event: OutboxEvent): Promise<void> {
    await db.outbox.delete(event.id!);
    const entityId = event.payload.id as string | undefined;
    if (entityId) {
      await this.clearPendingFlag(event.event_type, entityId, event.payload);
    }
    if (event.event_type === 'workout.completed') {
      const sid = event.payload.session_id as string;
      await db.workoutSessions.update(sid, { pending_sync: undefined });
    }
  }

  private async clearPendingFlag(
    eventType: OutboxEventType,
    entityId: string,
    payload: Record<string, unknown>,
  ): Promise<void> {
    switch (eventType) {
      case 'workout.started':
        await db.workoutSessions.update(entityId, { pending_sync: undefined });
        break;
      case 'session_exercise.added':
        await db.sessionExercises.update(entityId, { pending_sync: undefined });
        break;
      case 'set.logged':
        await db.workoutSets.update(entityId, { pending_sync: undefined });
        break;
      case 'measurement.created':
        await db.measurements.update(entityId, { pending_sync: undefined });
        break;
      case 'meal.created':
        await db.mealLogs.update(entityId, { pending_sync: undefined });
        break;
      case 'workout.completed':
        await db.workoutSessions.update(payload.session_id as string, { pending_sync: undefined });
        break;
    }
  }
}

export const outboxService = new OutboxService();
