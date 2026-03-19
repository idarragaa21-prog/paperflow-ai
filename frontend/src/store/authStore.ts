import { create } from 'zustand';
import { api } from '../services/api';
import { DEMO_MODE, demoUser } from '../services/demo';

export type UserMe = { id: string; email: string; full_name?: string | null; };
type AuthState = {
  user: UserMe | null; loading: boolean; error: string | null;
  checkAuth: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null, loading: false, error: null,

  checkAuth: async () => {
    if (DEMO_MODE) { set({ user: demoUser, loading: false }); return; }
    set({ loading: true, error: null });
    try { const r = await api.get('/auth/me'); set({ user: r.data as UserMe, loading: false }); }
    catch { set({ user: null, loading: false }); }
  },

  login: async (email, password) => {
    if (DEMO_MODE) {
      set({ loading: true });
      await new Promise(r => setTimeout(r, 600));
      set({ user: { ...demoUser, email }, loading: false, error: null });
      return;
    }
    set({ loading: true, error: null });
    try {
      await api.post('/auth/login', { email, password });
      const r = await api.get('/auth/me');
      set({ user: r.data as UserMe, loading: false });
    } catch (e: any) {
      set({ loading: false, error: e?.response?.data?.detail || 'Invalid credentials' });
    }
  },

  logout: async () => {
    if (DEMO_MODE) { set({ user: null }); return; }
    try { await api.post('/auth/logout'); } catch {}
    set({ user: null });
  },
}));
