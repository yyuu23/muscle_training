/**
 * Providers: QueryClient + cookie-session AuthProvider + Toasts.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';
import { AuthProvider } from '../features/auth/useAuth';
import { ToastProvider } from '../components/ui/Toast';
import { useTheme } from '../hooks/useTheme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true, // snapshot refresh on foreground (plan §8.6)
      staleTime: 5 * 60 * 1000,
    },
  },
});

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  useTheme(); // apply persisted/system theme before anything renders
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>{children}</ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
