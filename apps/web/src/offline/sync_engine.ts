/**
 * Sync engine (plan §8.5 / §8.6)
 *
 * Single write path to the server: POST /api/v1/sync/events.
 * - Batches ≤100, ordered by client_sequence per device
 * - Backoff 5s → 15s → 60s → 300s; 429 honors Retry-After
 * - Unknown outcomes (network error) retry the same event id verbatim
 * - dependency_pending stays retryable; permanent rejects become
 *   needs_attention and surface in the UI
 * - Parent failure stops child retries in the same cycle
 */

import { apiFetch, isNetworkError, APIError } from '../api/client';
import { db } from './database';
import { networkMonitor } from './network_monitor';
import { outboxService } from './outbox';

export type SyncStatus = 'idle' | 'syncing' | 'error' | 'offline';

export interface SyncStateSnapshot {
  status: SyncStatus;
  pendingCount: number;
  needsAttentionCount: number;
  lastSyncedAt: string | null;
}

type Listener = (state: SyncStateSnapshot) => void;

const BACKOFF_SECONDS = [5, 15, 60, 300];
const BATCH_LIMIT = 100;

interface EventResult {
  event_id: string;
  outcome: 'applied' | 'already_applied' | 'dependency_pending' | 'rejected';
  detail?: { error?: string; message?: string } | null;
  retryable?: boolean;
}

export class SyncEngine {
  private timer: number | null = null;
  private running = false;
  private userId: string | null = null;
  private listeners = new Set<Listener>();
  private state: SyncStateSnapshot = {
    status: 'idle',
    pendingCount: 0,
    needsAttentionCount: 0,
    lastSyncedAt: null,
  };

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  private emit(patch: Partial<SyncStateSnapshot>): void {
    this.state = { ...this.state, ...patch };
    this.listeners.forEach((l) => l(this.state));
  }

  async start(userId: string): Promise<void> {
    if (this.userId === userId && this.timer !== null) return;
    this.stop();
    this.userId = userId;

    // Startup recovery: stuck `sending` → pending (plan §8.5)
    await outboxService.restoreStuckSending();

    networkMonitor.subscribe((online) => {
      if (online) void this.sync();
      else this.emit({ status: 'offline' });
    });

    this.timer = window.setInterval(() => void this.sync(), 30000);
    await this.sync();
  }

  stop(): void {
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.userId = null;
    this.emit({ status: 'idle', pendingCount: 0 });
  }

  async sync(): Promise<void> {
    if (!this.userId || this.running) return;
    if (!networkMonitor.isOnline()) {
      this.emit({ status: 'offline' });
      return;
    }
    this.running = true;
    this.emit({ status: 'syncing' });

    try {
      let progressed = true;
      while (progressed) {
        progressed = await this.syncOneBatch();
      }
      const pending = await outboxService.getPendingCount(this.userId);
      const attention = await outboxService.getNeedsAttention(this.userId);
      this.emit({
        status: 'idle',
        pendingCount: pending,
        needsAttentionCount: attention.length,
        lastSyncedAt: new Date().toISOString(),
      });
    } catch (err) {
      this.emit({ status: isNetworkError(err) ? 'offline' : 'error' });
    } finally {
      this.running = false;
    }
  }

  /** Returns true when at least one event was acknowledged. */
  private async syncOneBatch(): Promise<boolean> {
    const userId = this.userId!;
    const now = Date.now();

    const due = await db.outbox
      .where('owner_user_id')
      .equals(userId)
      .and((e) => e.status === 'pending' && new Date(e.next_attempt_at).getTime() <= now)
      .sortBy('client_sequence');

    if (due.length === 0) return false;

    const batch = due.slice(0, BATCH_LIMIT);
    // Freeze on first send (plan §8.5): mark sending, record attempt
    await Promise.all(
      batch.map((e) =>
        db.outbox.update(e.id!, {
          status: 'sending' as const,
          first_attempt_at: e.first_attempt_at ?? new Date().toISOString(),
          attempt_count: e.attempt_count + 1,
        }),
      ),
    );

    const body = {
      events: batch.map((e) => ({
        event_id: e.event_id,
        device_id: e.device_id,
        client_sequence: e.client_sequence,
        event_type: e.event_type,
        client_created_at: e.created_at,
        payload: e.payload,
      })),
    };

    let results: EventResult[];
    try {
      const response = await apiFetch<{ results: EventResult[] }>('/sync/events', {
        method: 'POST',
        body,
      });
      results = response.results;
    } catch (err) {
      // Outcome unknown → restore pending, retry same ids verbatim
      await Promise.all(
        batch.map((e) =>
          db.outbox.update(e.id!, {
            status: 'pending' as const,
            last_error: err instanceof Error ? err.message : String(err),
            next_attempt_at: new Date(
              Date.now() + this.backoffMs(batch[0].attempt_count, err),
            ).toISOString(),
          }),
        ),
      );
      if (err instanceof APIError) throw err;
      return false;
    }

    const byEventId = new Map(results.map((r) => [r.event_id, r]));
    let anyAcknowledged = false;
    let blockedParents = new Set<string>();

    for (const event of batch) {
      const result = byEventId.get(event.event_id);
      if (!result) continue;

      if (result.outcome === 'applied' || result.outcome === 'already_applied') {
        await outboxService.acknowledge(event);
        anyAcknowledged = true;
      } else if (result.outcome === 'dependency_pending') {
        // Parent failed → don't retry children this cycle either
        if (blockedParents.size === 0) blockedParents = new Set([String(event.payload.session_id ?? '')]);
        await db.outbox.update(event.id!, {
          status: 'pending' as const,
          next_attempt_at: new Date(Date.now() + 15_000).toISOString(),
          last_error: result.detail?.message ?? '等待父记录同步',
        });
      } else {
        // rejected: permanent → needs_attention; else retry with backoff
        const retryable = result.retryable !== false;
        await db.outbox.update(event.id!, {
          status: retryable ? 'pending' : 'needs_attention',
          next_attempt_at: retryable
            ? new Date(Date.now() + this.backoffMs(event.attempt_count)).toISOString()
            : event.next_attempt_at,
          last_error: result.detail?.message ?? result.detail?.error ?? '事件被拒绝',
        });
        if (!retryable && event.payload.id) {
          blockedParents.add(String(event.payload.id));
        }
      }
    }
    return anyAcknowledged;
  }

  private backoffMs(attempt: number, err?: unknown): number {
    if (err instanceof APIError && err.retryAfterSeconds) {
      return err.retryAfterSeconds * 1000;
    }
    const seconds = BACKOFF_SECONDS[Math.min(attempt, BACKOFF_SECONDS.length - 1)];
    return seconds * 1000;
  }
}

export const syncEngine = new SyncEngine();
