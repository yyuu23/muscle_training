/**
 * Badge — status pill over the .badge-* component classes.
 */

import { ReactNode } from 'react';
import clsx from 'clsx';

export type BadgeTone = 'primary' | 'success' | 'warning' | 'danger' | 'neutral';

const TONE_CLASS: Record<BadgeTone, string> = {
  primary: 'badge-primary',
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
  neutral: 'badge-neutral',
};

export function Badge({ tone = 'neutral', children, className }: {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
}) {
  return <span className={clsx('badge', TONE_CLASS[tone], className)}>{children}</span>;
}
