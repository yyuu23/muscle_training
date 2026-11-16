/**
 * AmbientBackground — the site-wide atmosphere layer, mounted once in
 * AppShell (and on the auth pages). Recipe borrowed from the author's
 * blog (chunlongblog.cn "毛玻璃与粒子"):
 *
 *  1. a fixed 400%-size flowing gradient looping every 15s;
 *  2. two blurred color blobs for depth;
 *  3. floating DOM particles (no canvas): random position / duration /
 *     NEGATIVE delay so the screen is already full on first paint.
 *
 * Performance guardrails (same as the blog):
 *  - particle count halves on small screens;
 *  - prefers-reduced-motion removes the particle layer entirely
 *    (the global CSS rule also freezes every animation);
 *  - pure CSS animation → zero per-frame JS cost.
 */

import { CSSProperties, useMemo } from 'react';

const DESKTOP_COUNT = 16;
const MOBILE_COUNT = 8;

interface ParticleSpec {
  left: number; // vw
  size: number; // px
  duration: number; // s
  delay: number; // negative s
  opacity: number;
  colorVar: string;
}

function buildParticles(count: number): ParticleSpec[] {
  const colorVars = ['var(--particle-1)', 'var(--particle-2)', 'var(--particle-3)'];
  return Array.from({ length: count }, (_, i) => ({
    left: Math.random() * 100,
    size: 3 + Math.random() * 3,
    duration: 8 + Math.random() * 8,
    delay: -Math.random() * 16, // negative delay: mid-flight at load
    opacity: 0.45 + Math.random() * 0.4,
    colorVar: colorVars[i % colorVars.length],
  }));
}

export function AmbientBackground() {
  const particles = useMemo<ParticleSpec[] | null>(() => {
    if (
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return null;
    }
    const isSmall =
      typeof window !== 'undefined' &&
      window.matchMedia('(max-width: 768px)').matches;
    return buildParticles(isSmall ? MOBILE_COUNT : DESKTOP_COUNT);
  }, []);

  return (
    <div className="app-bg" aria-hidden>
      <div className="app-bg-gradient" />
      {/* depth blobs */}
      <div
        className="app-bg-blob"
        style={{ top: '-12vw', right: '-8vw', background: 'var(--primary)', opacity: 0.14 }}
      />
      <div
        className="app-bg-blob"
        style={{ bottom: '-16vw', left: '-10vw', background: 'var(--gradient-to)', opacity: 0.18 }}
      />
      {particles?.map((p, i) => (
        <span
          key={i}
          className="particle"
          style={
            {
              left: `${p.left}vw`,
              width: p.size,
              height: p.size,
              background: p.colorVar,
              boxShadow: `0 0 10px ${p.colorVar}`,
              animationDuration: `${p.duration}s`,
              animationDelay: `${p.delay}s`,
              '--p-opacity': p.opacity,
            } as CSSProperties
          }
        />
      ))}
    </div>
  );
}
