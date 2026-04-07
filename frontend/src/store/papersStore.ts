import { create } from 'zustand';

export type PaperStatusFilter = 'all' | 'ready' | 'processing' | 'pending' | 'failed';

type PapersState = {
  selectedIds: string[];
  statusFilter: PaperStatusFilter;
  searchQuery: string;
  setStatusFilter: (f: PaperStatusFilter) => void;
  setSearchQuery: (q: string) => void;
  toggleSelected: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
  isSelected: (id: string) => boolean;
};

export const usePapersStore = create<PapersState>((set, get) => ({
  selectedIds: [],
  statusFilter: 'all',
  searchQuery: '',

  setStatusFilter: (f) => set({ statusFilter: f }),

  setSearchQuery: (q) => set({ searchQuery: q }),

  toggleSelected: (id) =>
    set((s) =>
      s.selectedIds.includes(id)
        ? { selectedIds: s.selectedIds.filter((i) => i !== id) }
        : { selectedIds: [...s.selectedIds, id] },
    ),

  selectAll: (ids) => set({ selectedIds: ids }),

  clearSelection: () => set({ selectedIds: [] }),

  isSelected: (id) => get().selectedIds.includes(id),
}));
