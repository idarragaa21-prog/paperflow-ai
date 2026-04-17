import { create } from 'zustand';
import { api } from '../services/api';
import { getCookie } from '../services/cookies';
import { DEMO_MODE, demoUser } from '../services/demo';

export type UserMe = {
  id: string;
  email: string;
  full_name?: string | null;
  affiliation?: string | null;
  orcid?: string | null;
  signature_md?: string | null;
  language?: string | null;
  preferences?: Record<string, unknown> | null;
};
type AuthState = {
  user: UserMe | null; loading: boolean; initialized: boolean; error: string | null;
  checkAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null, loading: false, initialized: false, error: null,

  checkAuth: async () => {
    if (DEMO_MODE) {
      set({ user: demoUser, loading: false, initialized: true, error: null });
      return;
    }
    const hasSessionHint = Boolean(getCookie('csrf_token'));
    if (!hasSessionHint) {
      set({ user: null, loading: false, initialized: true, error: null });
      return;
    }
    set({ loading: true, error: null });
    try {
      const r = await api.get('/auth/me');
      set({ user: r.data as UserMe, loading: false, initialized: true });
    } catch {
      set({ user: null, loading: false, initialized: true });
    }
  },

  login: async (email, password) => {
    if (DEMO_MODE) {
      set({ loading: true });
      await new Promise(r => setTimeout(r, 600));
      set({ user: { ...demoUser, email }, loading: false, initialized: true, error: null });
      return;
    }
    set({ loading: true, error: null });
    try {
      await api.post('/auth/login', { email, password });
      const r = await api.get('/auth/me');
      set({ user: r.data as UserMe, loading: false, initialized: true });
    } catch (e: any) {
      set({ loading: false, initialized: true, error: e?.response?.data?.detail || 'Invalid credentials' });
    }
  },

  logout: async () => {
    if (DEMO_MODE) { set({ user: null, initialized: true }); return; }
    try { await api.post('/auth/logout'); } catch { /* best-effort logout */ }
    set({ user: null, initialized: true });
  },
}));
