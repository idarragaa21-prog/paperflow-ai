import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import DashboardPage from '../pages/DashboardPage';
import { useAuthStore } from '../store/authStore';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from '../services/api';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/projects/:projectId/research" element={<div>Project Research</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: { id: 'user-1', email: 'surgeon@example.com', full_name: 'Dr. Vega' },
      loading: false,
      initialized: true,
      error: null,
    });
  });

  it('renders recent project tile when project data exists', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/projects') {
        return {
          data: [
            { id: 'project-1', title: 'ACL Registry', clinical_area: 'Sports Medicine', archived: false },
          ],
        };
      }
      if (url === '/projects/project-1/dashboard') {
        return {
          data: {
            counts: { papers: 12, references: 8, notes: 4, meta_studies_current: 2 },
          },
        };
      }
      return { data: [] };
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('ACL Registry')).toBeInTheDocument();
      expect(screen.getByText('Sports Medicine')).toBeInTheDocument();
      expect(screen.getByText('Proyectos recientes')).toBeInTheDocument();
    });
  });

  it('shows empty state when there are no projects', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Aún no tienes proyectos')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Crear tu primer proyecto' })).toBeInTheDocument();
    });
  });

  it('navigates to a project when the project card is clicked', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/projects') {
        return {
          data: [
            { id: 'project-1', title: 'Shoulder Lab', clinical_area: 'Shoulder', archived: false },
          ],
        };
      }
      if (url === '/projects/project-1/dashboard') {
        return {
          data: {
            counts: { papers: 3, references: 2, notes: 1, meta_studies_current: 0 },
          },
        };
      }
      return { data: [] };
    });

    renderPage();

    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByText('Shoulder Lab')).toBeInTheDocument());
    await user.click(screen.getByText('Shoulder Lab'));

    await waitFor(() => {
      expect(screen.getByText('Project Research')).toBeInTheDocument();
    });
  });
});
