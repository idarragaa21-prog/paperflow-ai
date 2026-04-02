import { describe, expect, it } from 'vitest';
import { getWorkflowStages, type WorkflowStageKey } from '../components/WorkflowPrimitives';

describe('getWorkflowStages', () => {
  const projectId = 'test-project';

  it('initializes with default states when counts are empty or null', () => {
    const stages = getWorkflowStages(projectId, null);

    expect(stages.find((s) => s.key === 'research')?.state).toBe('ready');
    expect(stages.find((s) => s.key === 'library')?.state).toBe('pending');
    expect(stages.find((s) => s.key === 'reader')?.state).toBe('pending');
    expect(stages.find((s) => s.key === 'extract')?.state).toBe('pending');
    expect(stages.find((s) => s.key === 'write')?.state).toBe('pending');
    expect(stages.find((s) => s.key === 'analysis')?.state).toBe('pending');
  });

  it('overrides state to active for the current stage', () => {
    const stages = getWorkflowStages(projectId, null, 'reader' as WorkflowStageKey);

    expect(stages.find((s) => s.key === 'research')?.state).toBe('ready');
    expect(stages.find((s) => s.key === 'reader')?.state).toBe('active');
  });

  it('updates states correctly when papers are found', () => {
    const counts = { papers: 5 };
    const stages = getWorkflowStages(projectId, counts);

    expect(stages.find((s) => s.key === 'research')?.state).toBe('complete');
    expect(stages.find((s) => s.key === 'library')?.state).toBe('complete');
    expect(stages.find((s) => s.key === 'reader')?.state).toBe('ready');
    expect(stages.find((s) => s.key === 'extract')?.state).toBe('ready');
    expect(stages.find((s) => s.key === 'write')?.state).toBe('pending');
  });

  it('updates states correctly when notes are taken', () => {
    const counts = { papers: 5, notes: 2 };
    const stages = getWorkflowStages(projectId, counts);

    expect(stages.find((s) => s.key === 'reader')?.state).toBe('complete');
    expect(stages.find((s) => s.key === 'write')?.state).toBe('complete');
  });

  it('updates states correctly when meta studies are extracted', () => {
    const counts = { papers: 5, meta_studies_current: 1 };
    const stages = getWorkflowStages(projectId, counts);

    expect(stages.find((s) => s.key === 'extract')?.state).toBe('complete');
    expect(stages.find((s) => s.key === 'analysis')?.state).toBe('ready');
    expect(stages.find((s) => s.key === 'write')?.state).toBe('ready');
  });

  it('updates states correctly when writing is completed via references', () => {
    const counts = { papers: 5, references: 3 };
    const stages = getWorkflowStages(projectId, counts);

    expect(stages.find((s) => s.key === 'write')?.state).toBe('complete');
  });

  it('updates states correctly when presentations exist', () => {
    const counts = { presentations: 1 };
    const stages = getWorkflowStages(projectId, counts);

    expect(stages.find((s) => s.key === 'analysis')?.state).toBe('complete');
  });
});
