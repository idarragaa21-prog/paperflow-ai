import { beforeEach, describe, expect, it } from 'vitest';
import { usePapersStore } from '../store/papersStore';

const IDS = ['paper-1', 'paper-2', 'paper-3'];

describe('papersStore', () => {
  beforeEach(() => {
    usePapersStore.setState({ selectedIds: [], statusFilter: 'all', searchQuery: '' });
  });

  it('sets the status filter', () => {
    usePapersStore.getState().setStatusFilter('ready');
    expect(usePapersStore.getState().statusFilter).toBe('ready');
  });

  it('sets the search query', () => {
    usePapersStore.getState().setSearchQuery('meta-analysis');
    expect(usePapersStore.getState().searchQuery).toBe('meta-analysis');
  });

  it('toggles selection on and off', () => {
    usePapersStore.getState().toggleSelected('paper-1');
    expect(usePapersStore.getState().isSelected('paper-1')).toBe(true);
    usePapersStore.getState().toggleSelected('paper-1');
    expect(usePapersStore.getState().isSelected('paper-1')).toBe(false);
  });

  it('selectAll replaces the current selection', () => {
    usePapersStore.getState().toggleSelected('paper-1');
    usePapersStore.getState().selectAll(IDS);
    expect(usePapersStore.getState().selectedIds).toEqual(IDS);
  });

  it('clearSelection empties selectedIds', () => {
    usePapersStore.getState().selectAll(IDS);
    usePapersStore.getState().clearSelection();
    expect(usePapersStore.getState().selectedIds).toHaveLength(0);
  });

  it('isSelected returns false for unselected papers', () => {
    expect(usePapersStore.getState().isSelected('paper-99')).toBe(false);
  });
});
