/**
 * Skeleton — shimmer placeholder for loading states (AGENTS.md rule 7:
 * every page needs loading/error/empty states).
 */

import clsx from 'clsx';

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('skeleton', className)} aria-hidden />;
}

/** Card-shaped loading placeholder list. */
export function SkeletonCards({ count = 3, className }: { count?: number; className?: string }) {
  return (
    <div className={clsx('space-y-3', className)} role="status" aria-label="加载中">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="card p-5 space-y-3">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}
