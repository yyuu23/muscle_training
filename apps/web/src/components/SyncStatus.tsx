/**
 * Sync status indicator (plan §4.7 SyncStatus.tsx):
 * 本机已保存 / 待同步 / 同步中 / 已同步 / 需要处理
 */

import { useSyncStatus } from '../hooks/useSync';
import { useAuth } from '../features/auth/useAuth';

interface SyncStatusProps {
  className?: string;
}

export function SyncStatus({ className = '' }: SyncStatusProps) {
  const { user } = useAuth();
  const { status, pendingCount, needsAttentionCount, isOnline, lastSyncedAt, triggerSync } =
    useSyncStatus(user?.id ?? null);

  const state = (() => {
    if (!isOnline) {
      return { icon: '⚫', text: '离线 · 本机已保存', color: 'text-gray-500', bg: 'bg-gray-100' };
    }
    if (needsAttentionCount > 0) {
      return { icon: '🔴', text: `${needsAttentionCount} 条需处理`, color: 'text-red-600', bg: 'bg-red-50' };
    }
    if (status === 'syncing') {
      return { icon: '🔄', text: '同步中…', color: 'text-blue-600', bg: 'bg-blue-50' };
    }
    if (status === 'error') {
      return { icon: '⚠️', text: '同步出错', color: 'text-red-600', bg: 'bg-red-50' };
    }
    if (pendingCount > 0) {
      return { icon: '🟡', text: `${pendingCount} 条待同步`, color: 'text-amber-600', bg: 'bg-amber-50' };
    }
    return {
      icon: '🟢',
      text: lastSyncedAt ? '已同步' : '就绪',
      color: 'text-green-600',
      bg: 'bg-green-50',
    };
  })();

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${state.bg} ${state.color} text-sm font-medium`}
        title={lastSyncedAt ? `上次同步 ${new Date(lastSyncedAt).toLocaleTimeString('zh-CN')}` : undefined}
      >
        <span>{state.icon}</span>
        <span>{state.text}</span>
      </div>

      {isOnline && (pendingCount > 0 || needsAttentionCount > 0) && (
        <button
          onClick={triggerSync}
          disabled={status === 'syncing'}
          className="px-3 py-1.5 text-sm font-medium text-primary-600 hover:text-primary-700 disabled:opacity-50"
        >
          {status === 'syncing' ? '同步中…' : '立即同步'}
        </button>
      )}
    </div>
  );
}
