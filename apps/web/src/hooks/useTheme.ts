/**
 * Dual-theme controller (plan §8.1 设置): follows `prefers-color-scheme`
 * by default, with a manual override persisted to localStorage. Toggles the
 * `.dark` class on <html> which flips the CSS design tokens in global.css,
 * and keeps the PWA `theme-color` meta in sync.
 */

import { useCallback, useEffect, useState } from 'react';

export type ThemeMode = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'theme-mode';

function readStoredMode(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch {
    return 'system';
  }
}

function systemPrefersDark(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function applyTheme(mode: ThemeMode) {
  const dark = mode === 'system' ? systemPrefersDark() : mode === 'dark';
  const root = document.documentElement;
  root.classList.toggle('dark', dark);
  // Keep the browser UI chrome (PWA title bar) in sync.
  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (!meta) {
    meta = document.createElement('meta');
    meta.name = 'theme-color';
    document.head.appendChild(meta);
  }
  meta.content = dark ? '#0a0e16' : '#f4f5fa';
}

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() =>
    typeof window === 'undefined' ? 'system' : readStoredMode(),
  );

  // Apply on mount + whenever the mode changes.
  useEffect(() => {
    applyTheme(mode);
  }, [mode]);

  // Follow OS preference while in `system` mode.
  useEffect(() => {
    if (mode !== 'system') return;
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => applyTheme('system');
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  }, [mode]);

  const setTheme = useCallback((next: ThemeMode) => {
    try {
      if (next === 'system') localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* private mode: in-memory only */
    }
    setMode(next);
  }, []);

  return { mode, setTheme };
}
