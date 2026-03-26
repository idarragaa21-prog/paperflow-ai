import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import { getCookie } from './cookies';

const PRODUCTION_API_SENTINEL = '__REQUIRE_EXPLICIT_API_BASE_URL__';

function normalizeBaseUrl(url: string): string {
  return url.trim().replace(/\/+$/, '');
}

function resolveBaseUrl(): string {
  const explicitBaseUrl = String(import.meta.env.VITE_API_BASE_URL || '').trim();
  const sameOriginOptIn = String(import.meta.env.VITE_USE_SAME_ORIGIN_API || '')
    .trim()
    .toLowerCase() === 'true';
  const isRelativeBaseUrl = explicitBaseUrl.startsWith('/');

  if (explicitBaseUrl && explicitBaseUrl !== PRODUCTION_API_SENTINEL) {
    if (!import.meta.env.DEV && isRelativeBaseUrl && !sameOriginOptIn) {
      throw new Error(
        'Relative production API base URLs require VITE_USE_SAME_ORIGIN_API=true and a real /api proxy configuration.',
      );
    }
    if (!import.meta.env.DEV && isRelativeBaseUrl && explicitBaseUrl !== '/api') {
      throw new Error('PaperFlow same-origin mode only supports /api as the production API base URL.');
    }
    return normalizeBaseUrl(explicitBaseUrl);
  }

  if (import.meta.env.PROD) {
    if (sameOriginOptIn) {
      return '/api';
    }
    throw new Error(
      'PaperFlow production builds require VITE_API_BASE_URL unless you intentionally enable same-origin mode with VITE_USE_SAME_ORIGIN_API=true.',
    );
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
      (config.headers as Record<string, string>)['X-CSRF-Token'] = csrf;
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
    const original = error.config as (typeof error.config & { __isRetry?: boolean }) | undefined;

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
