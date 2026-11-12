/**
 * Account boundary (plan §8.7)
 *
 * - A user's outbox queue can never be submitted under another account.
 * - Logout clears in-memory private data; confirmed cache may go too.
 * - Unsynced events stay on-device but only become reachable again
 *   after re-authenticating as the original account.
 * - The new account's UI must never show the old account's data.
 */

import { db } from './database';
import { syncEngine } from './sync_engine';
import type { OutboxEvent } from './types';

export class AccountBoundaryError extends Error {
  constructor(message: string, public pendingCount: number) {
    super(message);
    this.name = 'AccountBoundaryError';
  }
}

export interface AccountSwitchResult {
  switched: boolean;
  pendingEvents?: OutboxEvent[];
}

export async function switchAccount(nextUserId: string): Promise<AccountSwitchResult> {
  // Any outbox rows NOT owned by the next user block the switch
  const foreign = await db.outbox
    .filter((e) => e.owner_user_id !== nextUserId && e.status !== 'needs_attention')
    .toArray();

  if (foreign.length > 0) {
    throw new AccountBoundaryError(
      `本机仍有 ${foreign.length} 条属于其他账号的未同步记录，只在本机保留；请先以原账号登录完成同步，或导出后再切换。`,
      foreign.length,
    );
  }

  syncEngine.stop();
  await db.syncMetadata.clear();
  return { switched: true };
}

/**
 * Logout: clear in-memory state. IndexedDB keeps per-user partitions;
 * pending events remain readable only after re-login as that user.
 */
export async function logoutCleanup(): Promise<void> {
  syncEngine.stop();
  await db.syncMetadata.clear();
}

/**
 * Whether data of any user other than `userId` exists locally
 * (used to guard against rendering stale cross-account caches).
 */
export async function hasForeignData(userId: string): Promise<boolean> {
  const [session, measurement, meal, outboxRow] = await Promise.all([
    db.workoutSessions.filter((r) => r.owner_user_id !== userId).limit(1).toArray(),
    db.measurements.filter((r) => r.owner_user_id !== userId).limit(1).toArray(),
    db.mealLogs.filter((r) => r.owner_user_id !== userId).limit(1).toArray(),
    db.outbox.filter((r) => r.owner_user_id !== userId).limit(1).toArray(),
  ]);
  return session.length + measurement.length + meal.length + outboxRow.length > 0;
}
