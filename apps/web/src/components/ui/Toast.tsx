/**
 * Toast — lightweight feedback system (记一组成功、同步完成等).
 * Fixed at the bottom above the nav bar; auto-dismiss with progress.
 */

import {
  createContext, useCallback, useContext, useMemo, useRef, useState, ReactNode,
} from 'react';
import { CheckCircleIcon, ExclamationCircleIcon, XMarkIcon } from '@heroicons/react/24/solid';
import clsx from 'clsx';

type ToastTone = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}

interface ToastApi {
  show: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastApi>({ show: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

const TONE_STYLE: Record<ToastTone, string> = {
  success: 'text-success',
  error: 'text-danger',
  info: 'text-primary',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const seq = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((message: string, tone: ToastTone = 'success') => {
    const id = ++seq.current;
    setToasts((prev) => [...prev.slice(-2), { id, tone, message }]);
    window.setTimeout(() => dismiss(id), 2600);
  }, [dismiss]);

  const api = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="fixed left-0 right-0 bottom-[calc(4.5rem+env(safe-area-inset-bottom))] lg:bottom-6 z-[60] flex flex-col items-center gap-2 pointer-events-none px-4"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className="animate-toast-in pointer-events-auto max-w-sm w-full sm:w-auto flex items-center gap-2.5 rounded-2xl glass border border-border-default shadow-strong px-4 py-3"
          >
            {t.tone === 'success' && <CheckCircleIcon className="w-5 h-5 shrink-0 text-success" />}
            {t.tone === 'error' && <ExclamationCircleIcon className="w-5 h-5 shrink-0 text-danger" />}
            {t.tone === 'info' && <span className="w-2 h-2 rounded-full bg-primary shrink-0" />}
            <p className={clsx('text-sm font-medium flex-1', TONE_STYLE[t.tone])}>{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              className="p-0.5 rounded-lg text-text-muted hover:text-text transition-colors"
              aria-label="关闭"
            >
              <XMarkIcon className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
