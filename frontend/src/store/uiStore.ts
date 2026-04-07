import { create } from 'zustand';

export type NotificationKind = 'success' | 'error' | 'info';

export type Notification = {
  id: string;
  kind: NotificationKind;
  title: string;
  message?: string;
};

type UiState = {
  notifications: Notification[];
  isGlobalLoading: boolean;
  openModals: string[];
  pushNotification: (n: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
  setGlobalLoading: (v: boolean) => void;
  openModal: (id: string) => void;
  closeModal: (id: string) => void;
  isModalOpen: (id: string) => boolean;
};

export const useUiStore = create<UiState>((set, get) => ({
  notifications: [],
  isGlobalLoading: false,
  openModals: [],

  pushNotification: (n) => {
    const id = Math.random().toString(36).slice(2);
    set((s) => ({ notifications: [{ ...n, id }, ...s.notifications].slice(0, 10) }));
  },

  removeNotification: (id) =>
    set((s) => ({ notifications: s.notifications.filter((n) => n.id !== id) })),

  setGlobalLoading: (v) => set({ isGlobalLoading: v }),

  openModal: (id) =>
    set((s) => ({ openModals: s.openModals.includes(id) ? s.openModals : [...s.openModals, id] })),

  closeModal: (id) =>
    set((s) => ({ openModals: s.openModals.filter((m) => m !== id) })),

  isModalOpen: (id) => get().openModals.includes(id),
}));
