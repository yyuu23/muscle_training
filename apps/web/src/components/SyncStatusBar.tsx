import { SyncStatus } from './SyncStatus';

export function SyncStatusBar() {
  return (
    <div className="glass border-b border-border-default px-4 py-2">
      <SyncStatus />
    </div>
  );
}
