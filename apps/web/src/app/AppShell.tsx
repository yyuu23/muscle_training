/**
 * App shell: auth guard (cookie session via /auth/me), sync status bar,
 * content area with bottom navigation (plan §8.1).
 */

import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { Navigation } from '../components/Navigation';
import { SyncStatusBar } from '../components/SyncStatusBar';
import { useAuth } from '../features/auth/useAuth';
import { registerUpdateManager } from '../pwa/update_manager';

export function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      navigate('/login', { replace: true });
    }
  }, [loading, user, navigate]);

  // SW update manager: never force-refresh while the user has unsaved input
  useEffect(() => {
    return registerUpdateManager();
  }, []);

  // Static PWA shell routes (login pages render outside this shell)
  const isAuthPath = location.pathname.startsWith('/login') || location.pathname.startsWith('/register');
  if (isAuthPath) {
    return <Outlet />;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <SyncStatusBar />
      <main className="flex-1 pb-16">
        <Outlet />
      </main>
      <Navigation />
    </div>
  );
}
