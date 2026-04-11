import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProjectLayout from '../components/ProjectLayout';
import { PROJECT_CONTENT_CHANGED_EVENT } from '../utils/projectEvents';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../hooks/useJobPolling', () => ({
  useJobPolling: () => ({
    isRunning: false,
    isDone: false,
    status: null,
  }),
}));

vi.mock('../components/Breadcrumb', () => ({
  Breadcrumb: () => <div data-testid="breadcrumb" />,
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

vi.mock('../components/meta/exportUtils', () => ({
  downloadBlob: vi.fn(),
}));

import { api } from '../services/api';

const PROJECT_ID = 'project-123';

function renderPage(initialEntry = `/projects/${PROJECT_ID}/research`) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/projects/:projectId" element={<ProjectLayout />}>
          <Route path="research" element={<div>Research workspace</div>} />
          <Route path="matrix" element={<div>Matrix workspace</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProjectLayout', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    let dashboardCalls = 0;
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === `/projects/${PROJECT_ID}`) {
        return {
          data: {
            id: PROJECT_ID,
            title: 'Proyecto Hombro',
            clinical_area: 'Hombro',
            runtime_mode: 'local_only',
            archived: false,
          },
        };
      }

      if (url === `/projects/${PROJECT_ID}/dashboard`) {
        dashboardCalls += 1;
        return {
          data: {
            project_id: PROJECT_ID,
            counts: {
              papers: dashboardCalls >= 2 ? 1 : 0,
              notes: 0,
              meta_studies_current: 0,
              references: 0,
            },
          },
        };
      }

      throw new Error(`Unexpected GET ${url}`);
    });
  });

  it('exposes Matrix support link and routes to matrix workspace', async () => {
    renderPage();

    await waitFor(() => expect(screen.getByText('Proyecto Hombro')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('link', { name: 'Matrix' }));

    await waitFor(() => {
      expect(screen.getByText('Matrix workspace')).toBeInTheDocument();
    });
  });

  it('refreshes project counts after a project content update event', async () => {
    renderPage();

    const getPapersMetricValue = () => {
      const label = screen.getByText(/^papers$/i);
      const card = label.closest('.rc-metric-card');
      return card?.querySelector('.rc-metric-card__value')?.textContent ?? null;
    };

    await waitFor(() => expect(getPapersMetricValue()).toBe('0'));

    act(() => {
      window.dispatchEvent(
        new CustomEvent(PROJECT_CONTENT_CHANGED_EVENT, {
          detail: { projectId: PROJECT_ID, reason: 'batch-download' },
        }),
      );
    });

    await waitFor(() => expect(getPapersMetricValue()).toBe('1'));
  });
});
