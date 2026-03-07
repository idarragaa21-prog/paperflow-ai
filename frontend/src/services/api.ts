import axios, { AxiosError } from 'axios';
import type { AxiosInstance } from 'axios';
import { getCookie } from './cookies';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

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
