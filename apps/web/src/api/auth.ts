/**
 * Auth API (plan §6.2) — typed against the generated contract.
 */

import type { components } from './generated/schema';
import { apiGet, apiPost, clearCsrfToken, setCsrfToken } from './client';

type Schemas = components['schemas'];

export type CurrentUser = Schemas['UserResponse'];
export type Capabilities = Schemas['CapabilitiesResponse'];

export async function login(username: string, password: string): Promise<Schemas['SessionTokenResponse']> {
  const result = await apiPost('/api/v1/auth/login', { username, password });
  setCsrfToken(result.csrf_token);
  return result;
}

export async function register(input: Schemas['RegisterRequest']): Promise<Schemas['SessionTokenResponse']> {
  const result = await apiPost('/api/v1/auth/register', input);
  setCsrfToken(result.csrf_token);
  return result;
}

export async function getMe(): Promise<Schemas['AuthMeResponse']> {
  const result = await apiGet('/api/v1/auth/me');
  setCsrfToken(result.csrf_token);
  return result;
}

export async function logout(): Promise<void> {
  await apiPost('/api/v1/auth/logout');
  clearCsrfToken();
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiPost('/api/v1/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
