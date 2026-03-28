import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import AnalysisPage from '../pages/AnalysisPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from '../services/api';

const PROJECT_ID = 'analysis-project-1';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/analysis`]}>
      <Routes>
        <Route path="/projects/:projectId/analysis" element={<AnalysisPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('AnalysisPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads datasets and persisted runs on mount', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/datasets') {
        return { data: [{ id: 'dataset-1', title: 'ACL registry', row_count: 12, column_count: 4 }] };
      }
      if (url === '/analysis-runs') {
        return { data: [{ id: 'run-1', title: 'ACL comparison', analysis_type: 'group_comparison', status: 'completed', warnings: [] }] };
      }
      return { data: [] };
    });

    renderPage();

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/datasets', { params: { project_id: PROJECT_ID } });
      expect(api.get).toHaveBeenCalledWith('/analysis-runs', { params: { project_id: PROJECT_ID } });
    });

    expect(await screen.findByTestId('analysis-dataset-select')).toHaveTextContent('ACL registry');
    expect(screen.getByTestId('analysis-run-run-1')).toHaveTextContent('ACL comparison');
  });

  it('creates a dataset with the entered JSON rows', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    vi.mocked(api.post).mockResolvedValue({
      data: { id: 'dataset-2', title: 'Manual dataset', row_count: 2, column_count: 2 },
    });

    renderPage();

    fireEvent.change(screen.getByTestId('dataset-title-input'), { target: { value: 'Manual dataset' } });
    fireEvent.change(screen.getByTestId('dataset-rows-input'), {
      target: { value: '[{"group":"A","value":12},{"group":"B","value":18}]' },
    });
    fireEvent.click(screen.getByTestId('dataset-create-button'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/datasets', {
        project_id: PROJECT_ID,
        title: 'Manual dataset',
        rows: [{ group: 'A', value: 12 }, { group: 'B', value: 18 }],
      });
    });
  });
});
