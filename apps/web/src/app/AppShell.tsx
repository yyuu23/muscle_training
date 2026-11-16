/**
 * App shell: ambient background, theme tokens, auth guard (cookie
 * session via /auth/me), desktop sidebar + mobile bottom navigation
 * (plan §8.1), route transition.
 */

import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { Navigation } from '../components/Navigation';
import { SyncStatusBar } from '../components/SyncStatusBar';
import { Sidebar } from '../components/Sidebar';
import { AmbientBackground } from '../components/AmbientBackground';
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
    <div className="min-h-screen lg:pl-64">
      <AmbientBackground />
      <Sidebar />
      <div className="flex flex-col min-h-screen">
        <div className="lg:hidden">
          <SyncStatusBar />
        </div>
        <main className="flex-1 pb-20 lg:pb-8">
          {/* Keyed remount → .page-enter transition replays on every route change */}
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </main>
        <div className="lg:hidden">
          <Navigation />
        </div>
      </div>
    </div>
  );
}
