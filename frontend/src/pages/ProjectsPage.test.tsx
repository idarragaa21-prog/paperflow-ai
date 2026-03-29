import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProjectsPage from './ProjectsPage';

// Mock api module
vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

// Mock demo mode (off)
vi.mock('../services/demo', () => ({
  DEMO_MODE: false,
  demoProjects: [],
  demoCounts: {},
}));

import { api } from '../services/api';

const mockProjects = [
  { id: 'p1', title: 'Project Alpha', description: 'Test desc', clinical_area: 'Oncology', archived: false },
  { id: 'p2', title: 'Project Beta', description: null, clinical_area: null, archived: false },
];

const mockArchivedProjects = [
  { id: 'p3', title: 'Project Gamma', description: null, clinical_area: null, archived: true },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjectsPage />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.get as any).mockImplementation((url: string) => {
    if (url === '/projects') return Promise.resolve({ data: mockProjects });
    if (url.includes('/dashboard')) return Promise.resolve({ data: { counts: { papers: 3, notes: 1, references: 2, meta_studies_current: 0, presentations: 0 } } });
    return Promise.reject(new Error('unknown url'));
  });
});

describe('ProjectsPage', () => {
  it('renders project list after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      expect(screen.getByText('Project Beta')).toBeInTheDocument();
    });
  });

  it('shows empty state when no active projects', async () => {
    (api.get as any).mockImplementation((url: string) => {
      if (url === '/projects') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: { counts: {} } });
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/no projects yet/i)).toBeInTheDocument();
    });
  });

  it('shows error state when API fails', async () => {
    (api.get as any).mockRejectedValue({ response: { data: { detail: 'Server error' } } });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/server error/i)).toBeInTheDocument();
    });
  });

  it('opens create project modal on button click', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Project Alpha'));
    const btn = screen.getByRole('button', { name: /new project/i });
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/project title/i)).toBeInTheDocument();
    });
  });

  it('creates a project and refreshes list', async () => {
    const newProject = { id: 'p-new', title: 'New Project', description: null, clinical_area: null, archived: false };
    (api.post as any).mockResolvedValue({ data: newProject });
    renderPage();
    await waitFor(() => screen.getByText('Project Alpha'));

    const btn = screen.getByRole('button', { name: /new project/i });
    fireEvent.click(btn);
    await waitFor(() => screen.getByPlaceholderText(/project title/i));

    fireEvent.change(screen.getByPlaceholderText(/project title/i), { target: { value: 'New Project' } });
    const createBtn = screen.getByRole('button', { name: /^create$/i });
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/projects', expect.objectContaining({ title: 'New Project' }));
    });
  });

  it('switches to archived tab and shows archived empty state', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Project Alpha'));

    const archivedTab = screen.getByRole('button', { name: /archived/i });
    fireEvent.click(archivedTab);

    await waitFor(() => {
      expect(screen.getByText(/archived projects will appear here/i)).toBeInTheDocument();
    });
  });
});
