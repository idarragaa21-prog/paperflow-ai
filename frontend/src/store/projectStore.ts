import { create } from 'zustand';
import type { Project } from '../types/api';

type ProjectState = {
  activeProjectId: string | null;
  projects: Project[];
  setActiveProjectId: (id: string | null) => void;
  setProjects: (projects: Project[]) => void;
  getActiveProject: () => Project | null;
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  activeProjectId: null,
  projects: [],

  setActiveProjectId: (id) => set({ activeProjectId: id }),

  setProjects: (projects) => set({ projects }),

  getActiveProject: () => {
    const { activeProjectId, projects } = get();
    return activeProjectId ? (projects.find((p) => p.id === activeProjectId) ?? null) : null;
  },
}));
