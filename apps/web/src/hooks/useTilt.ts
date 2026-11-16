/**
 * useTilt — subtle 3D card tilt following the pointer (borrowed from
 * chunlongblog.cn): perspective(1000px) + rotateX/Y ≤ ~4°, lerped via
 * rAF, plus a gentle lift while hovering.
 *
 * Only activates on desktop-class pointers (fine pointer + ≥lg width)
 * and never under prefers-reduced-motion. On touch devices the
 * handlers are inert — zero cost.
 */

import { useCallback, useEffect, useRef } from 'react';

const LERP = 0.12;
const EPS = 0.01;

export function useTilt<T extends HTMLElement>(maxDeg = 4) {
  const ref = useRef<T | null>(null);
  const anim = useRef({ rx: 0, ry: 0, trx: 0, try_: 0, raf: 0, hovering: false });
  const enabled = useRef(false);

  useEffect(() => {
    // Resolve activation once per mount (and on resize for cheap correctness)
    const check = () => {
      enabled.current =
        window.matchMedia('(pointer: fine)').matches &&
        window.matchMedia('(min-width: 1024px)').matches &&
        !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    };
    check();
    window.addEventListener('resize', check);
    return () => {
      window.removeEventListener('resize', check);
      cancelAnimationFrame(anim.current.raf);
    };
  }, []);

  const tick = useCallback(() => {
    const a = anim.current;
    a.rx += (a.trx - a.rx) * LERP;
    a.ry += (a.try_ - a.ry) * LERP;
    const el = ref.current;
    if (el) {
      const lift = a.hovering ? ' translateY(-2px)' : '';
      el.style.transform = `perspective(1000px) rotateX(${a.rx.toFixed(2)}deg) rotateY(${a.ry.toFixed(2)}deg)${lift}`;
    }
    if (Math.abs(a.trx - a.rx) > EPS || Math.abs(a.try_ - a.ry) > EPS) {
      a.raf = requestAnimationFrame(tick);
    } else {
      a.raf = 0;
      if (!a.hovering && el) el.style.transform = '';
    }
  }, []);

  const kick = useCallback(() => {
    if (!anim.current.raf) anim.current.raf = requestAnimationFrame(tick);
  }, [tick]);

  const onMouseMove = useCallback(
    (e: React.MouseEvent<T>) => {
      if (!enabled.current) return;
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const px = (e.clientX - rect.left) / rect.width - 0.5; // -0.5..0.5
      const py = (e.clientY - rect.top) / rect.height - 0.5;
      anim.current.try_ = px * maxDeg * 2; // rotateY follows x
      anim.current.trx = -py * maxDeg * 2; // rotateX inverts y
      anim.current.hovering = true;
      kick();
    },
    [kick, maxDeg],
  );

  const onMouseLeave = useCallback(() => {
    if (!enabled.current) return;
    anim.current.trx = 0;
    anim.current.try_ = 0;
    anim.current.hovering = false;
    kick();
  }, [kick]);

  return { ref, onMouseMove, onMouseLeave };
}
