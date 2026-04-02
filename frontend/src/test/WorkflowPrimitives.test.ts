import { describe, expect, it } from 'vitest';
import { getWorkflowStages, type WorkflowStageKey } from '../components/WorkflowPrimitives';

describe('WorkflowPrimitives.getWorkflowStages', () => {
  const projectId = 'test-project-123';

  it('returns default stages for empty counts and no current stage', () => {
    const stages = getWorkflowStages(projectId, null);

    expect(stages).toHaveLength(6);

    // Research should be ready, others pending
    expect(stages[0].key).toBe('research');
    expect(stages[0].state).toBe('ready');
    expect(stages[0].metricValue).toBe('Start');

    expect(stages[1].key).toBe('library');
    expect(stages[1].state).toBe('pending');
    expect(stages[1].metricValue).toBe('0');

    expect(stages[2].key).toBe('reader');
    expect(stages[2].state).toBe('pending');
    expect(stages[2].metricValue).toBe('Ask');

    expect(stages[3].key).toBe('extract');
    expect(stages[3].state).toBe('pending');
    expect(stages[3].metricValue).toBe('Review');

    expect(stages[4].key).toBe('write');
    expect(stages[4].state).toBe('pending');
    expect(stages[4].metricValue).toBe('Draft');

    expect(stages[5].key).toBe('analysis');
    expect(stages[5].state).toBe('pending');
    expect(stages[5].metricValue).toBe('Later');
  });

  it('updates states when papers are present', () => {
    const counts = { papers: 5 };
    const stages = getWorkflowStages(projectId, counts);

    const research = stages.find((s) => s.key === 'research');
    expect(research?.state).toBe('complete');
    expect(research?.metricValue).toBe('5');

    const library = stages.find((s) => s.key === 'library');
    expect(library?.state).toBe('complete');
    expect(library?.metricValue).toBe('5');

    const reader = stages.find((s) => s.key === 'reader');
    expect(reader?.state).toBe('ready'); // Ready because papers exist

    const extract = stages.find((s) => s.key === 'extract');
    expect(extract?.state).toBe('ready'); // Ready because papers exist
  });

  it('updates states when all counts are fully populated', () => {
    const counts = {
      papers: 10,
      notes: 3,
      references: 2,
      meta_studies_current: 4,
      presentations: 1,
    };
    const stages = getWorkflowStages(projectId, counts);

    expect(stages.every((s) => s.state === 'complete')).toBe(true);

    const write = stages.find((s) => s.key === 'write');
    expect(write?.metricValue).toBe('5'); // references (2) + notes (3)
  });

  it('marks the current stage as active', () => {
    const current: WorkflowStageKey = 'reader';
    const stages = getWorkflowStages(projectId, null, current);

    const reader = stages.find((s) => s.key === 'reader');
    expect(reader?.state).toBe('active');

    // Others should still have their default state
    const research = stages.find((s) => s.key === 'research');
    expect(research?.state).toBe('ready');
  });

  it('handles write state correctly with different combinations of notes and references', () => {
      // notes but no references
      let stages = getWorkflowStages(projectId, { notes: 1, references: 0, meta_studies_current: 0 });
      let write = stages.find((s) => s.key === 'write');
      expect(write?.state).toBe('complete');
      expect(write?.metricValue).toBe('1');

      // references but no notes
      stages = getWorkflowStages(projectId, { notes: 0, references: 2, meta_studies_current: 0 });
      write = stages.find((s) => s.key === 'write');
      expect(write?.state).toBe('complete');
      expect(write?.metricValue).toBe('2');

      // ready if no notes/references but meta_studies_current > 0
      stages = getWorkflowStages(projectId, { notes: 0, references: 0, meta_studies_current: 1 });
      write = stages.find((s) => s.key === 'write');
      expect(write?.state).toBe('ready');
      expect(write?.metricValue).toBe('Draft');
  })
});
