/**
 * ConfirmAction — dangerous operation confirmation (plan §4.7)
 */

import { useState, type ReactNode } from 'react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl">
            <div className="flex items-start gap-3 mb-4">
              <ExclamationTriangleIcon
                className={`w-6 h-6 shrink-0 ${danger ? 'text-red-500' : 'text-amber-500'}`}
              />
              <div>
                <h3 className="text-base font-semibold text-gray-900">{title}</h3>
                <p className="text-sm text-gray-500 mt-1">{description}</p>
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
              >
                {cancelLabel}
              </button>
              <button
                onClick={handleConfirm}
                disabled={busy}
                className={`px-4 py-2 text-sm rounded-lg text-white ${
                  danger ? 'bg-red-500 hover:bg-red-600' : 'bg-primary-600 hover:bg-primary-700'
                }`}
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
