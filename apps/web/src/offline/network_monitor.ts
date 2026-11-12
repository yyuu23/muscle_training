/**
 * Network status monitoring
 *
 * Monitors online/offline status and triggers sync when connection restored
 */

export type NetworkStatus = 'online' | 'offline';

export interface NetworkStatusListener {
  (status: NetworkStatus): void;
}

/**
 * Network monitor service
 */
export class NetworkMonitor {
  private listeners: Set<NetworkStatusListener> = new Set();
  private currentStatus: NetworkStatus;

  constructor() {
    this.currentStatus = navigator.onLine ? 'online' : 'offline';
    this.setupListeners();
  }

  /**
   * Setup browser event listeners
   */
  private setupListeners(): void {
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
  }

  /**
   * Cleanup listeners
   */
  destroy(): void {
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
  }

  /**
   * Handle online event
   */
  private handleOnline = (): void => {
    console.log('[NetworkMonitor] Connection restored');
    this.currentStatus = 'online';
    this.notifyListeners('online');
  };

  /**
   * Handle offline event
   */
  private handleOffline = (): void => {
    console.log('[NetworkMonitor] Connection lost');
    this.currentStatus = 'offline';
    this.notifyListeners('offline');
  };

  /**
   * Get current network status
   */
  getStatus(): NetworkStatus {
    return this.currentStatus;
  }

  /**
   * Check if online
   */
  isOnline(): boolean {
    return this.currentStatus === 'online';
  }

  /**
   * Subscribe to network status changes
   */
  subscribe(listener: NetworkStatusListener): () => void {
    this.listeners.add(listener);

    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Notify all listeners
   */
  private notifyListeners(status: NetworkStatus): void {
    this.listeners.forEach((listener) => {
      try {
        listener(status);
      } catch (error) {
        console.error('[NetworkMonitor] Listener error:', error);
      }
    });
  }
}

// Singleton instance
export const networkMonitor = new NetworkMonitor();
