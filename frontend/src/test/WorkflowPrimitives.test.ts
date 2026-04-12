import { describe, expect, it } from 'vitest';
import { getWorkflowStages, type WorkflowStageKey } from '../components/WorkflowPrimitives';

describe('WorkflowPrimitives.getWorkflowStages', () => {
  const projectId = 'test-project-123';

  it('returns default stages for empty counts and no current stage', () => {
    const stages = getWorkflowStages(projectId, null);

    expect(stages).toHaveLength(8);

    // Research should be ready, others pending.
    expect(stages[0].key).toBe('research');
    expect(stages[0].state).toBe('ready');
    expect(stages[0].metricValue).toBe('Start');

    expect(stages[1].key).toBe('library');
    expect(stages[1].state).toBe('pending');
    expect(stages[1].metricValue).toBe('0');

    expect(stages[2].key).toBe('reader');
    expect(stages[2].state).toBe('pending');
    expect(stages[2].metricValue).toBe('Ask');

    expect(stages[3].key).toBe('extraction');
    expect(stages[3].state).toBe('pending');
    expect(stages[3].metricValue).toBe('Review');

    expect(stages[4].key).toBe('matrix');
    expect(stages[4].state).toBe('pending');
    expect(stages[4].metricValue).toBe('Pending');

    expect(stages[5].key).toBe('meta_runs');
    expect(stages[5].state).toBe('pending');
    expect(stages[5].metricValue).toBe('Later');

    expect(stages[6].key).toBe('writing');
    expect(stages[6].state).toBe('pending');
    expect(stages[6].metricValue).toBe('Draft');

    expect(stages[7].key).toBe('artifacts');
    expect(stages[7].state).toBe('pending');
    expect(stages[7].metricValue).toBe('Pending');
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
    expect(reader?.state).toBe('ready');

    const extraction = stages.find((s) => s.key === 'extraction');
    expect(extraction?.state).toBe('ready');

    const matrix = stages.find((s) => s.key === 'matrix');
    expect(matrix?.state).toBe('ready');

    const metaRuns = stages.find((s) => s.key === 'meta_runs');
    expect(metaRuns?.state).toBe('pending');
  });

  it('updates states when all counts are fully populated', () => {
    const counts = {
      papers: 10,
      notes: 3,
      references: 2,
      meta_studies_current: 4,
    };
    const stages = getWorkflowStages(projectId, counts);

    const expectedByKey = {
      research: 'complete',
      library: 'complete',
      reader: 'complete',
      extraction: 'complete',
      matrix: 'complete',
      meta_runs: 'ready',
      writing: 'complete',
      artifacts: 'ready',
    } as const;

    for (const stage of stages) {
      expect(stage.state).toBe(expectedByKey[stage.key]);
    }

    const writing = stages.find((s) => s.key === 'writing');
    expect(writing?.metricValue).toBe('5'); // references (2) + notes (3)
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
    let writing = stages.find((s) => s.key === 'writing');
    expect(writing?.state).toBe('complete');
    expect(writing?.metricValue).toBe('1');

    // references but no notes
    stages = getWorkflowStages(projectId, { notes: 0, references: 2, meta_studies_current: 0 });
    writing = stages.find((s) => s.key === 'writing');
    expect(writing?.state).toBe('complete');
    expect(writing?.metricValue).toBe('2');

    // Ready if no notes/references but extracted studies are available.
    stages = getWorkflowStages(projectId, { notes: 0, references: 0, meta_studies_current: 1 });
    writing = stages.find((s) => s.key === 'writing');
    expect(writing?.state).toBe('ready');
    expect(writing?.metricValue).toBe('Draft');
  });
});
