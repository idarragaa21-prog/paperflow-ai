import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ProjectsPage from '../pages/ProjectsPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../ui/Dialog/useConfirm', () => ({
  useConfirm: () => vi.fn().mockResolvedValue(true),
}));

import { api } from '../services/api';

const PROJECTS = [
  { id: 'p1', title: 'ACL Project', clinical_area: 'Sports', archived: false },
  { id: 'p2', title: 'Archived Project', clinical_area: 'Hip', archived: true },
];

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProjectsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProjectsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/projects') return { data: PROJECTS };
      if (url === '/projects/p1/dashboard') {
        return { data: { counts: { papers: 4, references: 2, notes: 1, meta_studies_current: 1 } } };
      }
      throw new Error(`Unexpected GET ${url}`);
    });
    vi.mocked(api.post).mockResolvedValue({ data: {} });
  });

  it('creates a project from the inline form', async () => {
    renderPage();

    await userEvent.click(screen.getByRole('button', { name: /\+ New project/i }));
    await userEvent.type(screen.getByPlaceholderText(/Distal radius fracture outcomes/i), 'New Project');
    await userEvent.type(screen.getByPlaceholderText(/e.g. Orthopedics/i), 'Ortho');
    fireEvent.click(screen.getByRole('button', { name: 'Create project' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects', { title: 'New Project', clinical_area: 'Ortho' });
    });
  });

  it('archives an active project after confirmation', async () => {
    renderPage();

    await screen.findByText('ACL Project');
    fireEvent.click(screen.getByTitle('Archive project'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects/p1/archive');
    });
  });
});
