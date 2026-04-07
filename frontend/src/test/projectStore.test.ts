import { beforeEach, describe, expect, it } from 'vitest';
import { useProjectStore } from '../store/projectStore';

const PROJECT_A = { id: 'proj-1', title: 'Study A', archived: false };
const PROJECT_B = { id: 'proj-2', title: 'Study B', archived: false };

describe('projectStore', () => {
  beforeEach(() => {
    useProjectStore.setState({ activeProjectId: null, projects: [] });
  });

  it('sets the active project id', () => {
    useProjectStore.getState().setActiveProjectId('proj-1');
    expect(useProjectStore.getState().activeProjectId).toBe('proj-1');
  });

  it('clears the active project id', () => {
    useProjectStore.getState().setActiveProjectId('proj-1');
    useProjectStore.getState().setActiveProjectId(null);
    expect(useProjectStore.getState().activeProjectId).toBeNull();
  });

  it('sets the projects list', () => {
    useProjectStore.getState().setProjects([PROJECT_A, PROJECT_B]);
    expect(useProjectStore.getState().projects).toHaveLength(2);
  });

  it('getActiveProject returns null when no active id', () => {
    useProjectStore.getState().setProjects([PROJECT_A]);
    expect(useProjectStore.getState().getActiveProject()).toBeNull();
  });

  it('getActiveProject returns the matching project', () => {
    useProjectStore.getState().setProjects([PROJECT_A, PROJECT_B]);
    useProjectStore.getState().setActiveProjectId('proj-2');
    expect(useProjectStore.getState().getActiveProject()).toEqual(PROJECT_B);
  });

  it('getActiveProject returns null when id not in list', () => {
    useProjectStore.getState().setProjects([PROJECT_A]);
    useProjectStore.getState().setActiveProjectId('proj-999');
    expect(useProjectStore.getState().getActiveProject()).toBeNull();
  });
});
