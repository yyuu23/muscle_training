/**
 * API client (plan §4.7)
 *
 * - Same-origin /api/v1 with cookie credentials (HttpOnly session cookie)
 * - CSRF token on writes; X-Request-Id on every call
 * - Unified error envelope {error:{code,message,request_id,details}}
 * - 401 dispatches 'auth:expired'; 429 reads Retry-After
 */

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
export const API_PREFIX = '/api/v1';

export class APIError extends Error {
  status: number;
  code?: string;
  requestId?: string;
  details?: Record<string, unknown>;
  retryAfterSeconds?: number;

  constructor(
    message: string,
    status: number,
    opts?: { code?: string; requestId?: string; details?: Record<string, unknown>; retryAfterSeconds?: number },
  ) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.code = opts?.code;
    this.requestId = opts?.requestId;
    this.details = opts?.details;
    this.retryAfterSeconds = opts?.retryAfterSeconds;
  }
}

const CSRF_STORAGE_KEY = 'csrf_token';

export function getCsrfToken(): string | null {
  try {
    return localStorage.getItem(CSRF_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setCsrfToken(token: string): void {
  try {
    localStorage.setItem(CSRF_STORAGE_KEY, token);
  } catch {
    /* storage unavailable */
  }
}

export function clearCsrfToken(): void {
  try {
    localStorage.removeItem(CSRF_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

const WRITE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export interface FetchOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** Skip CSRF for pre-session endpoints (login/register/reset) */
  skipCsrf?: boolean;
  /** Raw body (e.g. file upload), disables JSON content type */
  rawBody?: BodyInit;
}

export async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const method = (opts.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'X-Request-Id': crypto.randomUUID(),
    ...opts.headers,
  };

  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (WRITE_METHODS.has(method) && !opts.skipCsrf) {
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  const response = await fetch(`${API_BASE}${API_PREFIX}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: opts.rawBody ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
  });

  // 204 no content
  if (response.status === 204) {
    return undefined as T;
  }

  let payload: unknown = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    payload = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const envelope = (payload as { error?: { code?: string; message?: string; request_id?: string; details?: Record<string, unknown> } })?.error;
    const error = new APIError(
      envelope?.message || `请求失败 (${response.status})`,
      response.status,
      {
        code: envelope?.code,
        requestId: envelope?.request_id,
        details: envelope?.details,
      },
    );
    if (response.status === 429) {
      const retryAfter = response.headers.get('Retry-After');
      if (retryAfter) error.retryAfterSeconds = parseInt(retryAfter, 10) || undefined;
    }
    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:expired'));
    }
    throw error;
  }

  return payload as T;
}

export function isNetworkError(err: unknown): boolean {
  return err instanceof TypeError; // fetch network failure
}

export function isAuthError(err: unknown): boolean {
  return err instanceof APIError && err.status === 401;
}

export function isConflictError(err: unknown): boolean {
  return err instanceof APIError && err.status === 409;
}

export function isRateLimited(err: unknown): boolean {
  return err instanceof APIError && err.status === 429;
}

/** Permanent validation rejections (no retry) from sync results */
export function isPermanentlyRejected(result: { outcome: string; retryable?: boolean }): boolean {
  return result.outcome === 'rejected' && result.retryable === false;
}
