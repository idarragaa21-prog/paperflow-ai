import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PapersPage from '../pages/PapersPage';

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ info: vi.fn(), error: vi.fn(), success: vi.fn() }),
}));

vi.mock('../ui/Dialog/useConfirm', () => ({
  useConfirm: () => ({ confirm: vi.fn().mockResolvedValue(true) }),
}));

vi.mock('../ui/Skeleton/Skeleton', () => ({
  Skeleton: () => <div data-testid="skeleton" />,
  SkeletonLines: () => <div data-testid="skeleton-lines" />,
}));

import { api } from '../services/api';

const PROJECT_ID = 'test-project-uuid-002';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/papers`]}>
        <Routes>
          <Route path="/projects/:projectId/papers" element={<PapersPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const MOCK_PAPERS = [
  {
    id: 'paper-1',
    title: 'Total knee arthroplasty outcomes',
    authors: 'Smith J, Doe A',
    journal: 'JBJS',
    publication_year: 2023,
    doi: '10.1000/tka.001',
    pmid: '11111111',
    filename: 'tka_outcomes.pdf',
    file_size_kb: 1200,
    is_processed: true,
    processing_status: 'ready',
    is_open_access: true,
    favorite: false,
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'paper-2',
    title: 'Rotator cuff repair long-term follow-up',
    authors: 'Jones B',
    journal: 'AJSM',
    publication_year: 2022,
    doi: '10.1000/rcr.002',
    pmid: null,
    filename: 'rcr_followup.pdf',
    file_size_kb: 850,
    is_processed: false,
    processing_status: 'processing',
    is_open_access: false,
    favorite: true,
    created_at: '2024-01-16T09:30:00Z',
  },
  {
    id: 'paper-3',
    title: 'ACL graft failure risk factors',
    authors: 'Garcia C',
    journal: 'Arthroscopy',
    publication_year: 2021,
    doi: null,
    pmid: '33333333',
    filename: 'acl_graft.pdf',
    file_size_kb: 620,
    is_processed: false,
    processing_status: 'failed',
    is_open_access: false,
    favorite: false,
    created_at: '2024-01-17T08:00:00Z',
  },
  {
    id: 'paper-4',
    title: 'Meniscus repair biomechanics',
    authors: 'Lee D',
    journal: 'Knee Surgery',
    publication_year: 2020,
    doi: '10.1000/men.004',
    pmid: '44444444',
    filename: 'meniscus.pdf',
    file_size_kb: 400,
    is_processed: false,
    processing_status: 'uploaded',
    is_open_access: false,
    favorite: false,
    created_at: '2024-01-18T07:00:00Z',
  },
];

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('PapersPage — render', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_PAPERS });
  });

  it('renders the Library page title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Library')).toBeInTheDocument();
    });
  });

  it('fetches papers for the correct project', async () => {
    renderPage();
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining(PROJECT_ID),
      );
    });
  });

  it('renders all paper titles', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Total knee arthroplasty outcomes')).toBeInTheDocument();
      expect(screen.getByText('Rotator cuff repair long-term follow-up')).toBeInTheDocument();
      expect(screen.getByText('ACL graft failure risk factors')).toBeInTheDocument();
    });
  });
});

describe('PapersPage — status badges', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_PAPERS });
  });

  it('shows "Ready" badge for processed papers', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Ready')).toBeInTheDocument();
    });
  });

  it('shows "Processing" badge for in-progress papers', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Processing')).toBeInTheDocument();
    });
  });

  it('shows "Failed" badge for failed papers', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Failed')).toBeInTheDocument();
    });
  });

  it('shows "Pending" badge for uploaded-but-unprocessed papers', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Pending')).toBeInTheDocument();
    });
  });
});

describe('PapersPage — status filter', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_PAPERS });
  });

  it('shows all papers with "all" filter (default)', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Total knee arthroplasty outcomes')).toBeInTheDocument();
      expect(screen.getByText('Rotator cuff repair long-term follow-up')).toBeInTheDocument();
      expect(screen.getByText('ACL graft failure risk factors')).toBeInTheDocument();
    });
  });

  it('filters to only ready papers when "ready" filter selected', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Total knee arthroplasty outcomes'));

    const filterSelect = screen.getByRole('combobox');
    fireEvent.change(filterSelect, { target: { value: 'ready' } });

    await waitFor(() => {
      expect(screen.getByText('Total knee arthroplasty outcomes')).toBeInTheDocument();
      expect(screen.queryByText('ACL graft failure risk factors')).not.toBeInTheDocument();
    });
  });

  it('filters to only failed papers when "failed" filter selected', async () => {
    renderPage();
    await waitFor(() => screen.getByText('ACL graft failure risk factors'));

    const filterSelect = screen.getByRole('combobox');
    fireEvent.change(filterSelect, { target: { value: 'failed' } });

    await waitFor(() => {
      expect(screen.getByText('ACL graft failure risk factors')).toBeInTheDocument();
      expect(screen.queryByText('Total knee arthroplasty outcomes')).not.toBeInTheDocument();
    });
  });
});

describe('PapersPage — search', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: MOCK_PAPERS });
  });

  it('filters papers by title text search', async () => {
    renderPage();
    await waitFor(() => screen.getByText('Total knee arthroplasty outcomes'));

    const searchInput = screen.getByPlaceholderText(/Buscar t[ií]tulo/i);
    fireEvent.change(searchInput, { target: { value: 'ACL' } });

    await waitFor(() => {
      expect(screen.getByText('ACL graft failure risk factors')).toBeInTheDocument();
      expect(screen.queryByText('Total knee arthroplasty outcomes')).not.toBeInTheDocument();
    });
  });
});

describe('PapersPage — empty state', () => {
  it('shows empty state when no papers', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    renderPage();
    await waitFor(() => {
      // Empty state renders something — page doesn't crash
      expect(screen.getByText('Library')).toBeInTheDocument();
    });
  });
});
