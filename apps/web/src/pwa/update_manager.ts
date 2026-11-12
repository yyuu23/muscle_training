/**
 * Update manager (plan §4.7): a new service worker never force-refreshes
 * a page with unsaved form input. Instead show a "稍后更新" banner.
 */

interface UpdateBanner {
  show(): void;
}

let banner: UpdateBanner | null = null;

function userHasUnsavedInput(): boolean {
  const active = document.activeElement;
  if (active instanceof HTMLElement) {
    const tag = active.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
    if (active.isContentEditable) return true;
  }
  return false;
}

function mountBanner(onApply: () => void): UpdateBanner {
  const el = document.createElement('div');
  el.className = 'fixed top-0 left-0 right-0 z-[60] bg-gray-900 text-white text-sm px-4 py-2.5 flex items-center justify-between gap-3';
  el.innerHTML = `
    <span>新版本已就绪</span>
    <span>
      <button data-action="apply" style="text-decoration:underline;font-weight:600;margin-right:12px;">立即更新</button>
      <button data-action="later" style="opacity:.7;">稍后</button>
    </span>
  `;
  el.querySelector('[data-action="apply"]')?.addEventListener('click', onApply);
  el.querySelector('[data-action="later"]')?.addEventListener('click', () => el.remove());
  document.body.appendChild(el);
  return {
    show() {
      if (!document.body.contains(el)) document.body.appendChild(el);
    },
  };
}

/**
 * Registers a periodic SW-update check. When an update is waiting:
 * - unsaved input → defer, show banner
 * - otherwise → apply immediately on next navigation/idle
 * Returns a cleanup function.
 */
export function registerUpdateManager(): () => void {
  if (!('serviceWorker' in navigator)) return () => {};

  let cleanup = false;

  const check = async () => {
    if (cleanup) return;
    const registration = await navigator.serviceWorker.getRegistration().catch(() => undefined);
    if (!registration?.waiting) return;

    const apply = () => {
      registration.waiting?.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    };

    if (userHasUnsavedInput()) {
      banner ??= mountBanner(apply);
      banner.show();
    } else {
      apply();
    }
  };

  void check();
  const interval = window.setInterval(check, 60_000);
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    // Applied updates navigate naturally; nothing to force here.
  });

  return () => {
    cleanup = true;
    clearInterval(interval);
  };
}
