/**
 * Sync status indicator (plan §4.7 SyncStatus.tsx):
 * 本机已保存 / 待同步 / 同步中 / 已同步 / 需要处理
 */

import {
  CloudArrowDownIcon, CloudArrowUpIcon, ArrowPathIcon,
  ExclamationCircleIcon, CheckCircleIcon, SignalSlashIcon,
} from '@heroicons/react/24/solid';
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
      return { Icon: SignalSlashIcon, text: '离线 · 本机已保存', cls: 'text-text-secondary bg-surface-2', spin: false };
    }
    if (needsAttentionCount > 0) {
      return { Icon: ExclamationCircleIcon, text: `${needsAttentionCount} 条需处理`, cls: 'text-danger bg-danger-soft', spin: false };
    }
    if (status === 'syncing') {
      return { Icon: ArrowPathIcon, text: '同步中…', cls: 'text-primary bg-primary-soft', spin: true };
    }
    if (status === 'error') {
      return { Icon: ExclamationCircleIcon, text: '同步出错', cls: 'text-danger bg-danger-soft', spin: false };
    }
    if (pendingCount > 0) {
      return { Icon: CloudArrowUpIcon, text: `${pendingCount} 条待同步`, cls: 'text-warning bg-warning-soft', spin: false };
    }
    return {
      Icon: lastSyncedAt ? CheckCircleIcon : CloudArrowDownIcon,
      text: lastSyncedAt ? '已同步' : '就绪',
      cls: 'text-success bg-success-soft',
      spin: false,
    };
  })();

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div
        className={`flex items-center gap-1.5 px-3 py-1 rounded-full ${state.cls} text-xs font-medium animate-fade-in`}
        title={lastSyncedAt ? `上次同步 ${new Date(lastSyncedAt).toLocaleTimeString('zh-CN')}` : undefined}
      >
        <state.Icon className={`w-3.5 h-3.5 ${state.spin ? 'animate-spin' : ''}`} />
        <span>{state.text}</span>
      </div>

      {isOnline && (pendingCount > 0 || needsAttentionCount > 0) && (
        <button
          onClick={triggerSync}
          disabled={status === 'syncing'}
          className="px-2.5 py-1 text-xs font-semibold text-primary hover:underline underline-offset-2 disabled:opacity-50"
        >
          {status === 'syncing' ? '同步中…' : '立即同步'}
        </button>
      )}
    </div>
  );
}
