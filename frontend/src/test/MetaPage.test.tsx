import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MetaPage from '../pages/MetaPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../hooks/useJobPolling', () => ({
  useJobPolling: () => ({ status: null }),
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

vi.mock('../components/meta/StudyViewer', () => ({
  default: ({ studyId }: { studyId: string }) => <div>RoB grid for {studyId}</div>,
}));

vi.mock('../components/meta/exportUtils', () => ({
  downloadBlob: vi.fn(),
}));

import { api } from '../services/api';

const PROJECT_ID = 'project-meta-1';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/meta`]}>
      <Routes>
        <Route path="/projects/:projectId/meta" element={<MetaPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('MetaPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === `/meta/batches?project_id=${PROJECT_ID}`) {
        return {
          data: [{ id: 'batch-1', title: 'ACL batch', status: 'completed', created_at: '2026-03-01T10:00:00Z' }],
        };
      }
      if (url === `/meta/studies?project_id=${PROJECT_ID}`) {
        return {
          data: [
            {
              id: 'study-1',
              paper_title: 'ACL graft meta-analysis',
              paper_filename: 'acl.pdf',
              version: 1,
              extraction_confidence: 0.93,
              rob_auto_generated: true,
            },
          ],
        };
      }
      if (url === `/meta/exports?project_id=${PROJECT_ID}`) {
        return { data: [] };
      }
      if (url === '/meta/batches/batch-1/items') {
        return { data: [] };
      }
      return { data: [] };
    });
    vi.mocked(api.post).mockResolvedValue({ data: { job_id: 'export-job-1' } });
  });

  it('loads studies correctly', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('ACL graft meta-analysis')).toBeInTheDocument();
    });
  });

  it('shows the RoB grid when a study is selected', async () => {
    renderPage();
    const user = userEvent.setup();

    await waitFor(() => expect(screen.getByText('ACL graft meta-analysis')).toBeInTheDocument());
    await user.click(screen.getByText('ACL graft meta-analysis'));

    await waitFor(() => {
      expect(screen.getByText('RoB grid for study-1')).toBeInTheDocument();
      expect(screen.getByText('RoB auto')).toBeInTheDocument();
    });
  });

  it('exports to Excel without errors', async () => {
    renderPage();

    const exportButton = await screen.findByRole('button', { name: 'Export Excel' });
    fireEvent.click(exportButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/meta/export', {
        project_id: PROJECT_ID,
        batch_id: null,
      });
      expect(screen.getByText(/Export job enqueued/i)).toBeInTheDocument();
    });
  });
});
