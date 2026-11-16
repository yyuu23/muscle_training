/**
 * ProgressRing — circular countdown for the rest timer (训练记录页).
 * SVG stroke-dashoffset driven; seconds number pulses in the center.
 * Colors are theme-aware (works on light & dark surfaces).
 */

export function ProgressRing({
  total,
  remaining,
  size = 64,
}: {
  total: number;
  remaining: number;
  size?: number;
}) {
  const stroke = 5;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const progress = total > 0 ? remaining / total : 0;
  const done = remaining <= 0;

  return (
    <div className="relative animate-scale-in" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="currentColor" strokeWidth={stroke}
          className="text-surface-2"
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="currentColor" strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - progress)}
          className={done ? 'text-success' : 'text-primary'}
          style={{ transition: 'stroke-dashoffset 1s linear' }}
        />
      </svg>
      <span
        key={remaining}
        className={`absolute inset-0 flex items-center justify-center font-mono font-bold tabular-nums animate-count-pop ${
          done ? 'text-success' : 'text-primary'
        }`}
        style={{ fontSize: size / 3.4 }}
      >
        {remaining}
      </span>
    </div>
  );
}

/** Simple linear progress bar. */
export function ProgressBar({ value, max, className }: { value: number; max: number; className?: string }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className={`h-2 rounded-full bg-surface-2 overflow-hidden ${className ?? ''}`}>
      <div
        className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
        style={{ width: `${pct}%` }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      />
    </div>
  );
}
