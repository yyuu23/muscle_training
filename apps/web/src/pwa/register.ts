/**
 * Service Worker registration
 */

/**
 * Register service worker
 */
export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!('serviceWorker' in navigator)) {
    console.warn('[PWA] Service Worker not supported');
    return null;
  }

  try {
    const registration = await navigator.serviceWorker.register('/service-worker.js', {
      scope: '/',
    });

    console.log('[PWA] Service Worker registered:', registration.scope);

    // Check for updates
    registration.addEventListener('updatefound', () => {
      const newWorker = registration.installing;
      if (!newWorker) return;

      newWorker.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          // New version available
          console.log('[PWA] New version available');
          notifyUpdate();
        }
      });
    });

    return registration;
  } catch (error) {
    console.error('[PWA] Service Worker registration failed:', error);
    return null;
  }
}

/**
 * Unregister service worker
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) {
    return false;
  }

  const registration = await navigator.serviceWorker.getRegistration();
  if (registration) {
    return registration.unregister();
  }

  return false;
}

/**
 * Notify user about update
 */
function notifyUpdate(): void {
  // Dispatch custom event
  window.dispatchEvent(new CustomEvent('sw-update-available'));

  // Show notification (you can customize this)
  if (confirm('New version available! Reload to update?')) {
    window.location.reload();
  }
}

/**
 * Check if app is running as PWA
 */
export function isPWA(): boolean {
  const iosNavigator = window.navigator as Navigator & { standalone?: boolean };
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    iosNavigator.standalone === true
  );
}

/** Minimal shape of the non-standard beforeinstallprompt event. */
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: string }>;
}

/**
 * Prompt user to install PWA
 */
export function setupInstallPrompt(): void {
  let deferredPrompt: InstallPromptEvent | null = null;

  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent default install prompt
    e.preventDefault();
    deferredPrompt = e as InstallPromptEvent;

    // Dispatch custom event
    window.dispatchEvent(new CustomEvent('pwa-installable'));
  });

  // Expose install function globally
  (window as Window & { installPWA?: () => Promise<void> }).installPWA = async () => {
    if (!deferredPrompt) {
      console.log('[PWA] Install prompt not available');
      return;
    }

    // Show install prompt
    await deferredPrompt.prompt();

    // Wait for user choice
    const { outcome } = await deferredPrompt.userChoice;
    console.log('[PWA] User choice:', outcome);

    deferredPrompt = null;
  };
}
