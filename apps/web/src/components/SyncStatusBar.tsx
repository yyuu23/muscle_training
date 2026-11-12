import { SyncStatus } from './SyncStatus';

export function SyncStatusBar() {
  return (
    <div className="bg-white border-b border-gray-200 px-4 py-2">
      <SyncStatus />
    </div>
  );
}
