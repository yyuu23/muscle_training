/**
 * Sheet — mobile bottom sheet / centered dialog built on Headless UI.
 * Replaces window.prompt() usages (e.g. discomfort reporting).
 */

import { Fragment, ReactNode } from 'react';
import { Dialog, DialogPanel, DialogTitle, Transition, TransitionChild } from '@headlessui/react';

export interface SheetProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** Bottom sheet on mobile-friendly forms, centered modal otherwise. */
  variant?: 'bottom' | 'center';
}

export function Sheet({ open, onClose, title, children, variant = 'bottom' }: SheetProps) {
  return (
    <Transition show={open} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-50">
        {/* Backdrop */}
        <TransitionChild
          as={Fragment}
          enter="ease-out duration-200"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-150"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/45 backdrop-blur-[2px]" aria-hidden />
        </TransitionChild>

        <div className="fixed inset-0 flex items-end justify-center sm:items-center sm:p-4">
          <TransitionChild
            as={Fragment}
            enter="ease-out duration-200"
            enterFrom="opacity-0 translate-y-8 sm:translate-y-0 sm:scale-95"
            enterTo="opacity-100 translate-y-0 sm:scale-100"
            leave="ease-in duration-150"
            leaveFrom="opacity-100 translate-y-0 sm:scale-100"
            leaveTo="opacity-0 translate-y-8 sm:translate-y-0 sm:scale-95"
          >
            <DialogPanel
              className={`w-full sm:max-w-md bg-surface border border-border-default rounded-t-3xl sm:rounded-3xl shadow-strong p-5 pb-[calc(1.25rem+env(safe-area-inset-bottom))] animate-slide-up ${
                variant === 'bottom' ? 'sm:mx-0' : ''
              }`}
            >
              {/* drag handle */}
              <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-text-muted/40 sm:hidden" />
              <DialogTitle className="text-base font-semibold text-text mb-3">{title}</DialogTitle>
              {children}
            </DialogPanel>
          </TransitionChild>
        </div>
      </Dialog>
    </Transition>
  );
}
