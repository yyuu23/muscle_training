/**
 * Error & empty states (plan §8.1: pages must handle error states).
 */

import { ExclamationTriangleIcon, ArrowPathIcon, InboxIcon } from '@heroicons/react/24/outline';
import { Button } from './ui/Button';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({ title = '加载失败', message, onRetry }: ErrorStateProps) {
  return (
    <div className="card p-6 text-center animate-scale-in">
      <span className="inline-flex w-12 h-12 rounded-2xl bg-warning-soft text-warning items-center justify-center mb-3">
        <ExclamationTriangleIcon className="w-6 h-6" />
      </span>
      <h3 className="text-base font-semibold text-text mb-1">{title}</h3>
      <p className="text-sm text-text-secondary mb-4">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <ArrowPathIcon className="w-4 h-4" />
          重试
        </Button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="text-center py-10 px-4 animate-fade-in">
      <span className="inline-flex w-14 h-14 rounded-3xl bg-surface-2 text-text-muted items-center justify-center mb-3">
        <InboxIcon className="w-7 h-7" />
      </span>
      <p className="text-sm font-medium text-text">{title}</p>
      {description && <p className="text-xs text-text-muted mt-1.5 max-w-xs mx-auto leading-relaxed">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
