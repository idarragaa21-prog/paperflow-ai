import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import { getCookie } from './cookies';

/**
 * API base URL resolution:
 *   1. Explicit VITE_API_BASE_URL env var (always wins)
 *   2. In production without demo mode: same-origin (reverse proxy)
 *   3. In development: http://127.0.0.1:8000
 *   4. In demo mode: empty string (calls are intercepted by demo layer anyway)
 */
function resolveBaseUrl(): string {
  const explicit = import.meta.env.VITE_API_BASE_URL;
  if (explicit) return explicit;

  const isDemoMode = import.meta.env.VITE_DEMO_MODE === 'true';

  if (import.meta.env.PROD) {
    if (!isDemoMode) {
      console.warn(
        '[PaperFlow] VITE_API_BASE_URL not set in production. ' +
        'Using same-origin. Set VITE_API_BASE_URL if backend is on a different host.',
      );
    }
    return '';
  }

  return 'http://127.0.0.1:8000';
}

const API_BASE_URL = resolveBaseUrl();

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

// CSRF: send header on mutating requests
api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase();
  const isMutating = ['post', 'put', 'patch', 'delete'].includes(method);
  if (isMutating) {
    const csrf = getCookie('csrf_token');
    if (csrf) {
      config.headers = config.headers ?? {};
      (config.headers as any)['X-CSRF-Token'] = csrf;
    }
  }
  return config;
});

let refreshing: Promise<void> | null = null;

// Use a "raw" client without interceptors to avoid recursive refresh loops.
const raw = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

async function refreshSession(): Promise<void> {
  await raw.post('/auth/refresh');
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const original = error.config as any;

    const url = String(original?.url || '');
    const isAuthEndpoint = url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/logout');

    if (status === 401 && original && !original.__isRetry && !isAuthEndpoint) {
      original.__isRetry = true;

      try {
        if (!refreshing) {
          refreshing = refreshSession().finally(() => {
            refreshing = null;
          });
        }
        await refreshing;
        return api.request(original);
      } catch {
        // refresh failed -> propagate original 401
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  },
);

export function isApiError(e: unknown): e is AxiosError {
  return axios.isAxiosError(e);
}
