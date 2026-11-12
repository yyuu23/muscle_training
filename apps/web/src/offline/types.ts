/**
 * Offline types (plan §8.3)
 *
 * All user data keys include owner_user_id.
 * Outbox events freeze after first send attempt.
 */

export type OutboxStatus = 'pending' | 'sending' | 'needs_attention';

export type OutboxEventType =
  | 'workout.started'
  | 'session_exercise.added'
  | 'set.logged'
  | 'workout.completed'
  | 'measurement.created'
  | 'meal.created';

export interface OutboxEvent {
  /** Local auto-increment id */
  id?: number;
  /** Stable event id (UUID) — server dedup key */
  event_id: string;
  owner_user_id: string;
  device_id: string;
  client_sequence: number;
  event_type: OutboxEventType;
  /** Frozen after first send attempt */
  payload: Record<string, unknown>;
  payload_hash: string;
  status: OutboxStatus;
  first_attempt_at: string | null;
  attempt_count: number;
  next_attempt_at: string;
  last_error: string | null;
  created_at: string;
}

// --- Local record mirrors -------------------------------------------------

export interface LocalWorkoutSession {
  id: string;
  owner_user_id: string;
  plan_version_id: string | null;
  plan_day_key: string | null;
  started_at: string;
  completed_at: string | null;
  status: 'in_progress' | 'completed' | 'abandoned';
  precheck: Record<string, unknown> | null;
  notes: string | null;
  version: number;
  /** true while the outbox event for this record is not yet acknowledged */
  pending_sync?: boolean;
}

export interface LocalSessionExercise {
  id: string;
  owner_user_id: string;
  session_id: string;
  exercise_id: string;
  plan_item_id: string | null;
  position: number;
  equipment_label: string | null;
  override_reason: string | null;
  completion_status: 'not_recorded' | 'partial' | 'completed' | 'skipped';
  version: number;
  pending_sync?: boolean;
}

export interface LocalWorkoutSet {
  id: string;
  owner_user_id: string;
  session_exercise_id: string;
  set_index: number;
  set_kind: 'warmup' | 'work';
  status: 'completed' | 'skipped' | 'failed';
  load_kg: string | null;
  load_mode: string | null;
  reps: number | null;
  duration_seconds: number | null;
  rir: number | null;
  discomfort_report: string | null;
  performed_at: string;
  version: number;
  pending_sync?: boolean;
}

export interface LocalMeasurement {
  id: string;
  owner_user_id: string;
  measurement_type: 'weight' | 'body_fat_percentage' | 'circumference' | 'other';
  value: string;
  unit: string;
  observed_at: string;
  source: string;
  notes: string | null;
  version: number;
  pending_sync?: boolean;
}

export interface LocalMealLog {
  id: string;
  owner_user_id: string;
  occurred_at: string;
  meal_type: string | null;
  description: string;
  items: unknown[] | null;
  nutrition: Record<string, unknown> | null;
  nutrition_source: 'user_label' | 'user_estimate' | 'model_estimate' | 'unknown';
  version: number;
  pending_sync?: boolean;
}

export interface LocalProfile {
  id: string;
  owner_user_id: string;
  version: number;
  goal: string | null;
  height_cm: number | null;
  training_experience_months: number | null;
  sessions_per_week: number | null;
  minutes_per_session: number | null;
  available_weekdays: number[] | null;
  equipment: string[] | null;
  available_load_increments: string[] | null;
}

export interface LocalPlan {
  id: string;
  owner_user_id: string;
  sequence_number: number;
  status: 'draft' | 'active' | 'superseded' | 'archived';
  content: Record<string, unknown>;
  activated_at: string | null;
}

export interface LocalExercise {
  id: string;
  slug: string;
  content_version: number;
  name: string;
  aliases: string[];
  movement_pattern: string | null;
  equipment_tags: string[];
  metric_type: 'reps' | 'duration';
  load_mode: string;
  instructions: string[];
  common_errors: string[];
}

export interface LocalProfileFact {
  id: string;
  owner_user_id: string;
  kind: string;
  fact_key: string;
  value: string;
  provenance: string;
}

export interface FormDraft {
  key: string;
  owner_user_id: string;
  data: Record<string, unknown>;
  updated_at: string;
}

export interface SyncMetadataRecord {
  key: string;
  value: string;
  updated_at: string;
}
