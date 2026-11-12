/**
 * Auth API (plan §6.2)
 */

import { apiFetch, setCsrfToken, clearCsrfToken } from './client';

export interface CurrentUser {
  id: string;
  username: string;
  display_name: string;
  role: 'admin' | 'member';
  timezone: string;
  status: string;
  created_at: string;
}

export interface Capabilities {
  chat_model_configured: boolean;
  embedding_model_configured: boolean;
  transcription_configured: boolean;
  content_ready: boolean;
  storage_configured: boolean;
  offline_recording_available: boolean;
}

interface SessionTokenResponse {
  user: CurrentUser;
  csrf_token: string;
}

interface AuthMeResponse {
  user: CurrentUser;
  csrf_token: string;
  capabilities: Capabilities;
}

export async function login(username: string, password: string): Promise<SessionTokenResponse> {
  const result = await apiFetch<SessionTokenResponse>('/auth/login', {
    method: 'POST',
    body: { username, password },
    skipCsrf: true,
  });
  setCsrfToken(result.csrf_token);
  return result;
}

export async function register(input: {
  username: string;
  password: string;
  display_name: string;
  invite_code: string;
}): Promise<SessionTokenResponse> {
  const result = await apiFetch<SessionTokenResponse>('/auth/register', {
    method: 'POST',
    body: input,
    skipCsrf: true,
  });
  setCsrfToken(result.csrf_token);
  return result;
}

export async function getMe(): Promise<AuthMeResponse> {
  const result = await apiFetch<AuthMeResponse>('/auth/me');
  setCsrfToken(result.csrf_token);
  return result;
}

export async function logout(): Promise<void> {
  await apiFetch('/auth/logout', { method: 'POST' });
  clearCsrfToken();
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiFetch('/auth/change-password', {
    method: 'POST',
    body: { current_password: currentPassword, new_password: newPassword },
  });
}
