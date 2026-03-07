import { create } from 'zustand';
import { api } from '../services/api';

export type UserMe = {
  id: string;
  email: string;
  full_name?: string | null;
};

type AuthState = {
  user: UserMe | null;
  loading: boolean;
  error: string | null;
  checkAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  error: null,

  checkAuth: async () => {
    set({ loading: true, error: null });
    try {
      const r = await api.get('/auth/me');
      set({ user: r.data as UserMe, loading: false });
    } catch (e) {
      set({ user: null, loading: false });
    }
  },

  login: async (email: string, password: string) => {
    set({ loading: true, error: null });
    try {
      await api.post('/auth/login', { email, password });
      const r = await api.get('/auth/me');
      set({ user: r.data as UserMe, loading: false });
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Login failed';
      set({ error: String(msg), loading: false });
      throw e;
    }
  },

  logout: async () => {
    set({ loading: true, error: null });
    try {
      await api.post('/auth/logout');
    } finally {
      set({ user: null, loading: false });
    }
  },
}));
