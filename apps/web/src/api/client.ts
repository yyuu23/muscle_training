/**
 * API client (plan §4.7)
 *
 * - Same-origin /api/v1 with cookie credentials (HttpOnly session cookie)
 * - CSRF token on writes; X-Request-Id on every call
 * - Unified error envelope {error:{code,message,request_id,details}}
 * - 401 dispatches 'auth:expired'; 429 reads Retry-After
 *
 * Contract-driven helpers (apiGet/apiPost/apiPatch/apiPut/apiDelete) take
 * FULL paths from the generated OpenAPI schema (src/api/generated/schema.ts,
 * the single source of truth per plan §4.3): path literals, request bodies
 * and response bodies are all compile-time checked against the contract.
 */

import type { paths } from './generated/schema';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

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

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** Raw body (e.g. file upload), disables JSON content type */
  rawBody?: BodyInit;
}

async function request<T>(fullPath: string, opts: RequestOptions = {}): Promise<T> {
  const method = (opts.method || 'GET').toUpperCase();
  const headers: Record<string, string> = {
    'X-Request-Id': crypto.randomUUID(),
    ...opts.headers,
  };

  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  if (WRITE_METHODS.has(method)) {
    // No token exists yet for pre-session writes (login/register);
    // attaching nothing behaves identically to skipping.
    const csrf = getCsrfToken();
    if (csrf) headers['X-CSRF-Token'] = csrf;
  }

  const response = await fetch(`${API_BASE}${fullPath}`, {
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

// ----------------------------------------------------------------------
// Contract-driven typed helpers (plan §4.3 — the generated schema is the
// single source of truth for paths, request bodies and response bodies).
// ----------------------------------------------------------------------

type Method = 'get' | 'post' | 'patch' | 'put' | 'delete';

/** The operation object for path P under method M (undefined if absent). */
type Op<P extends keyof paths, M extends Method> =
  paths[P] extends { [K in M]: infer O } ? O : undefined;

/** Response body of the first 2xx code declared on the operation. */
type OkBody<P extends keyof paths, M extends Method> =
  Op<P, M> extends { responses: { 200: { content: { 'application/json': infer R } } } } ? R
    : Op<P, M> extends { responses: { 201: { content: { 'application/json': infer R } } } } ? R
    : Op<P, M> extends { responses: { 202: { content: { 'application/json': infer R } } } } ? R
    : undefined;

/** JSON request body the operation expects (undefined when none). */
type ReqBody<P extends keyof paths, M extends Method> =
  Op<P, M> extends { requestBody: { content: { 'application/json': infer B } } } ? B : undefined;

/** Path must actually declare this method. */
type HasMethod<P extends keyof paths, M extends Method> =
  paths[P] extends { [K in M]: unknown } ? P : never;

/** Runtime {param} substitution in a contract path literal. */
function substitute(path: string, params?: Record<string, string | number>): string {
  if (!params) return path;
  return path.replace(/\{([a-z_]+)\}/gi, (whole, key: string) => {
    if (!(key in params)) return whole;
    return encodeURIComponent(String(params[key]));
  });
}

export type PathParams = Record<string, string | number>;

export function apiGet<P extends keyof paths & string>(
  path: HasMethod<P, 'get'>,
  params?: PathParams,
): Promise<OkBody<P, 'get'>> {
  return request<OkBody<P, 'get'>>(substitute(path, params));
}

export function apiPost<P extends keyof paths & string>(
  path: HasMethod<P, 'post'>,
  body?: ReqBody<P, 'post'>,
  params?: PathParams,
): Promise<OkBody<P, 'post'>> {
  return request<OkBody<P, 'post'>>(substitute(path, params), {
    method: 'POST',
    body: body as Record<string, unknown> | undefined,
  });
}

export function apiPatch<P extends keyof paths & string>(
  path: HasMethod<P, 'patch'>,
  body?: ReqBody<P, 'patch'>,
  params?: PathParams,
): Promise<OkBody<P, 'patch'>> {
  return request<OkBody<P, 'patch'>>(substitute(path, params), {
    method: 'PATCH',
    body: body as Record<string, unknown> | undefined,
  });
}

export function apiPut<P extends keyof paths & string>(
  path: HasMethod<P, 'put'>,
  rawBody: BodyInit,
  params?: PathParams,
  headers?: Record<string, string>,
): Promise<OkBody<P, 'put'>> {
  return request<OkBody<P, 'put'>>(substitute(path, params), { method: 'PUT', rawBody, headers });
}

export function apiDelete<P extends keyof paths & string>(
  path: HasMethod<P, 'delete'>,
  params?: PathParams,
): Promise<OkBody<P, 'delete'>> {
  return request<OkBody<P, 'delete'>>(substitute(path, params), { method: 'DELETE' });
}
