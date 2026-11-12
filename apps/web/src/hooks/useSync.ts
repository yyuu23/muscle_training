/**
 * Sync hooks — bind the SyncEngine lifecycle to the current user.
 */

import { useCallback, useEffect, useState } from 'react';
import { syncEngine, type SyncStateSnapshot } from '../offline/sync_engine';
import { networkMonitor } from '../offline/network_monitor';

export function useSyncStatus(userId: string | null): SyncStateSnapshot & {
  isOnline: boolean;
  triggerSync: () => void;
} {
  const [state, setState] = useState<SyncStateSnapshot>({
    status: 'idle',
    pendingCount: 0,
    needsAttentionCount: 0,
    lastSyncedAt: null,
  });
  const [isOnline, setIsOnline] = useState(() => networkMonitor.isOnline());

  useEffect(() => {
    const unsubscribe = syncEngine.subscribe(setState);
    const unsubscribeNetwork = networkMonitor.subscribe((status) => setIsOnline(status === 'online'));
    return () => {
      unsubscribe();
      unsubscribeNetwork();
    };
  }, []);

  useEffect(() => {
    if (!userId) return;
    void syncEngine.start(userId);
  }, [userId]);

  const triggerSync = useCallback(() => {
    void syncEngine.sync();
  }, []);

  return { ...state, isOnline, triggerSync };
}

export function usePendingCount(userId: string | null): number {
  const { pendingCount } = useSyncStatus(userId);
  return pendingCount;
}
