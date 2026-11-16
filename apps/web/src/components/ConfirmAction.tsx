/**
 * ConfirmAction — dangerous operation confirmation (plan §4.7)
 */

import { useState, type ReactNode } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/solid';

interface ConfirmActionProps {
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void | Promise<void>;
  children: (trigger: (e: React.MouseEvent) => void) => ReactNode;
}

export function ConfirmAction({
  title,
  description,
  confirmLabel = '确认',
  cancelLabel = '取消',
  danger = false,
  onConfirm,
  children,
}: ConfirmActionProps) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleConfirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      {children((e) => {
        e.stopPropagation();
        setOpen(true);
      })}

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-[2px] p-4 animate-fade-in">
          <div className="bg-surface border border-border-default rounded-3xl max-w-sm w-full p-6 shadow-strong animate-scale-in">
            <div className="flex items-start gap-3 mb-5">
              <span
                className={`inline-flex w-10 h-10 rounded-2xl items-center justify-center shrink-0 ${
                  danger ? 'bg-danger-soft text-danger' : 'bg-warning-soft text-warning'
                }`}
              >
                <ExclamationTriangleIcon className="w-5 h-5" />
              </span>
              <div>
                <h3 className="text-base font-semibold text-text">{title}</h3>
                <p className="text-sm text-text-secondary mt-1 leading-relaxed">{description}</p>
              </div>
            </div>
            <div className="flex gap-2.5 justify-end">
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="btn btn-secondary btn-sm"
              >
                {cancelLabel}
              </button>
              <button
                onClick={handleConfirm}
                disabled={busy}
                className={`btn btn-sm text-white ${danger ? 'btn-danger' : 'btn-primary'}`}
              >
                {busy ? '处理中…' : confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
