/**
 * Auth hooks — cookie session flow (plan §9.2)
 *
 * No tokens in localStorage; the session lives in an HttpOnly cookie.
 * CSRF token is cached and attached by the API client on writes.
 */

import { createContext, useContext, useEffect, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import * as authApi from '../../api/auth';
import { logoutCleanup, switchAccount } from '../../offline/account_boundary';
import { fetchAndApplySnapshot } from '../../offline/snapshot_cache';

interface AuthState {
  user: authApi.CurrentUser | null;
  loading: boolean;
  capabilities: authApi.Capabilities | null;
  refresh: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  capabilities: null,
  refresh: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => authApi.getMe(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // Snapshot refresh on login success (plan §8.6)
  useEffect(() => {
    if (data?.user) {
      void fetchAndApplySnapshot(data.user.id).catch(() => {
        /* offline: cached data stays */
      });
    }
  }, [data?.user]);

  // Session expired → clear state (event dispatched by api client)
  useEffect(() => {
    const handler = () => {
      queryClient.setQueryData(['auth', 'me'], null);
    };
    window.addEventListener('auth:expired', handler);
    return () => window.removeEventListener('auth:expired', handler);
  }, [queryClient]);

  return (
    <AuthContext.Provider
      value={{
        user: data?.user ?? null,
        loading: isLoading,
        capabilities: data?.capabilities ?? null,
        refresh: () => void refetch(),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

export function useLogin() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { username: string; password: string }) => authApi.login(data.username, data.password),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['auth'] });
      await fetchAndApplySnapshot(result.user.id).catch(() => {});
      navigate('/today');
    },
  });
}

export function useRegister() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { username: string; password: string; display_name: string; invite_code: string }) =>
      authApi.register(data),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['auth'] });
      await fetchAndApplySnapshot(result.user.id).catch(() => {});
      navigate('/onboarding');
    },
  });
}

export function useLogout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  return useMutation({
    mutationFn: async () => {
      await authApi.logout().catch(() => {});
      if (user) {
        await switchAccount(user.id).catch(() => {});
      }
      await logoutCleanup();
    },
    onSettled: () => {
      queryClient.setQueryData(['auth', 'me'], null);
      queryClient.clear();
      navigate('/login');
    },
  });
}
