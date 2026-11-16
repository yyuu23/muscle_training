/**
 * Card + StatCard (animated count-up number tile).
 */

import { ReactNode } from 'react';
import clsx from 'clsx';
import { useCountUp } from '../../hooks/useCountUp';

export interface CardProps {
  children: ReactNode;
  className?: string;
  interactive?: boolean;
  hover?: boolean;
  style?: React.CSSProperties;
  onClick?: () => void;
}

export function Card({ children, className, interactive, hover = true, style, onClick }: CardProps) {
  return (
    <div
      className={clsx('card', hover && 'card-hover', interactive && 'card-interactive', className)}
      style={style}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

export interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: number;
  /** Rendered instead of the number when there is no data yet. */
  empty?: boolean;
  unit?: string;
  tone?: 'primary' | 'success' | 'warning';
  /** Stagger index — delays the entrance animation. */
  index?: number;
}

const TONE_CLASS = {
  primary: 'bg-primary-soft text-primary dark:bg-primary-soft-2 dark:text-primary-contrast',
  success: 'bg-success-soft text-success',
  warning: 'bg-warning-soft text-warning',
} as const;

export function StatCard({ icon, label, value, empty, unit, tone = 'primary', index = 0 }: StatCardProps) {
  const animated = useCountUp(value);
  return (
    <div
      className="card p-4 animate-slide-up"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-2 ${TONE_CLASS[tone]}`}>
        {icon}
      </div>
      <div className={`text-2xl font-bold tabular-nums animate-count-pop ${empty ? 'text-text-muted' : ''}`} key={value}>
        {empty ? '—' : Math.round(animated)}
      </div>
      <div className="text-xs text-text-muted mt-0.5">
        {label}
        {!empty && unit && <span className="text-text-muted/70"> ({unit})</span>}
      </div>
    </div>
  );
}
