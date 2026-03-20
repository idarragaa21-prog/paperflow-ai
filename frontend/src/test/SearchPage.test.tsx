import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SearchPage from '../pages/SearchPage';

// ── Mocks ───────────────────────────────────────────────────────────────────

vi.mock('../services/api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ info: vi.fn(), error: vi.fn(), success: vi.fn() }),
}));

vi.mock('../ui/Skeleton/Skeleton', () => ({
  Skeleton: () => <div data-testid="skeleton" />,
  SkeletonLines: () => <div data-testid="skeleton-lines" />,
}));

import { api } from '../services/api';

const PROJECT_ID = 'test-project-uuid-001';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/search`]}>
      <Routes>
        <Route path="/projects/:projectId/search" element={<SearchPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

const MOCK_RESPONSE = {
  count: 2,
  cached: false,
  sources: ['pubmed', 'europepmc'],
  query_translation: null,
  results: [
    {
      pmid: '12345678',
      pmcid: 'PMC1234',
      doi: '10.1000/test.001',
      title: 'ACL reconstruction hamstring vs BPTB meta-analysis',
      authors: ['Smith J', 'Doe A'],
      journal: 'AJSM',
      pub_year: 2023,
      abstract: 'Background: This study compares hamstring and BPTB grafts.',
      source: 'pubmed',
      is_open_access: true,
      oa_url: 'https://ncbi.nlm.nih.gov/pmc/articles/PMC1234/pdf/',
      relevance_score: 0.87,
    },
    {
      pmid: null,
      pmcid: null,
      doi: '10.1000/test.002',
      title: 'Rotator cuff repair systematic review',
      authors: ['Jones B'],
      journal: 'JBJS',
      pub_year: 2021,
      abstract: null,
      source: 'europepmc',
      is_open_access: false,
      oa_url: null,
      relevance_score: 0.54,
    },
  ],
};

// ── Tests ────────────────────────────────────────────────────────────────────

describe('SearchPage — render', () => {
  it('renders the page title', () => {
    renderPage();
    expect(screen.getByText('Research Search')).toBeInTheDocument();
  });

  it('renders the query input', () => {
    renderPage();
    expect(screen.getByPlaceholderText(/ACL reconstruction/i)).toBeInTheDocument();
  });

  it('search button is disabled with empty query', () => {
    renderPage();
    const btn = screen.getByRole('button', { name: /^Search$/i });
    expect(btn).toBeDisabled();
  });

  it('search button is disabled with query shorter than 3 chars', async () => {
    renderPage();
    const input = screen.getByPlaceholderText(/ACL reconstruction/i);
    await userEvent.type(input, 'AC');
    expect(screen.getByRole('button', { name: /^Search$/i })).toBeDisabled();
  });

  it('search button enables when query >= 3 chars', async () => {
    renderPage();
    const input = screen.getByPlaceholderText(/ACL reconstruction/i);
    await userEvent.type(input, 'ACL');
    expect(screen.getByRole('button', { name: /^Search$/i })).not.toBeDisabled();
  });
});

describe('SearchPage — API call', () => {
  beforeEach(() => {
    vi.mocked(api.post).mockResolvedValue({ data: MOCK_RESPONSE });
  });

  it('calls /search/federated with correct payload', async () => {
    renderPage();
    const input = screen.getByPlaceholderText(/ACL reconstruction/i);
    await userEvent.type(input, 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/search/federated',
        expect.objectContaining({
          project_id: PROJECT_ID,
          query: 'ACL hamstring',
          max_results: 20,
        }),
      );
    });
  });

  it('renders result titles after successful search', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis')).toBeInTheDocument();
      expect(screen.getByText('Rotator cuff repair systematic review')).toBeInTheDocument();
    });
  });

  it('shows result count', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(screen.getByText(/Results:/)).toBeInTheDocument();
    });
  });

  it('displays OA badge for open access papers', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(screen.getByText('OA')).toBeInTheDocument();
    });
  });

  it('displays relevance score when present', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(screen.getByText(/Score: 87%/)).toBeInTheDocument();
    });
  });
});

describe('SearchPage — oa_url in download payload', () => {
  beforeEach(() => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: MOCK_RESPONSE });
    vi.mocked(api.post).mockResolvedValue({ data: { duplicate: false } });
  });

  it('sends oa_url in /papers/download payload', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));

    const downloadBtns = screen.getAllByRole('button', { name: /Download OA PDF/i });
    fireEvent.click(downloadBtns[0]);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/papers/download',
        expect.objectContaining({
          project_id: PROJECT_ID,
          doi: '10.1000/test.001',
          pmid: '12345678',
          oa_url: 'https://ncbi.nlm.nih.gov/pmc/articles/PMC1234/pdf/',
        }),
      );
    });
  });
});

describe('SearchPage — filters', () => {
  it('shows filter panel when Filters button is clicked', async () => {
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /Filters/i }));
    expect(screen.getByPlaceholderText(/e.g. Lancet/i)).toBeInTheDocument();
    expect(screen.getByText(/Open Access only/i)).toBeInTheDocument();
  });

  it('includes year_from filter in API payload when set', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: MOCK_RESPONSE });
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /Filters/i }));

    const yearFrom = screen.getByPlaceholderText(/e.g. 2018/i);
    await userEvent.clear(yearFrom);
    await userEvent.type(yearFrom, '2020');

    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL knee');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/search/federated',
        expect.objectContaining({
          filters: expect.objectContaining({ year_from: 2020 }),
        }),
      );
    });
  });

  it('includes open_access_only in payload when checked', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: MOCK_RESPONSE });
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: /Filters/i }));

    const checkbox = screen.getByRole('checkbox');
    await userEvent.click(checkbox);

    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL knee');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/search/federated',
        expect.objectContaining({
          filters: expect.objectContaining({ open_access_only: true }),
        }),
      );
    });
  });
});

describe('SearchPage — error handling', () => {
  it('displays error message on API failure', async () => {
    vi.mocked(api.post).mockRejectedValue({
      response: { data: { detail: 'Rate limit exceeded' } },
    });
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL knee');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => {
      expect(screen.getByText('Rate limit exceeded')).toBeInTheDocument();
    });
  });
});

// ── CRITICAL FLOW: search → download → traceability ─────────────────────────

describe('SearchPage — download traceability', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: [] }); // history
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE }) // search
      .mockResolvedValueOnce({
        data: {
          id: 'paper-uuid-001',
          project_id: PROJECT_ID,
          title: 'ACL reconstruction hamstring vs BPTB meta-analysis',
          doi: '10.1000/test.001',
          source_provider: 'unpaywall',
          oa_url: 'https://unpaywall.org/resolved.pdf',
          duplicate: false,
          filename: 'paper.pdf',
          file_path: 'papers/paper.pdf',
          content_hash: 'abc123',
        },
      });
  });

  it('shows "Downloaded" with source provider after successful download', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));

    const downloadBtns = screen.getAllByRole('button', { name: /Download OA PDF/i });
    fireEvent.click(downloadBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('✓ Downloaded')).toBeInTheDocument();
    });
  });

  it('shows resolved URL in traceability panel', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));

    const downloadBtns = screen.getAllByRole('button', { name: /Download OA PDF/i });
    fireEvent.click(downloadBtns[0]);

    await waitFor(() => {
      expect(screen.getByText(/https:\/\/unpaywall\.org\/resolved\.pdf/)).toBeInTheDocument();
    });
  });

  it('shows "Already in project" for duplicate downloads', async () => {
    vi.mocked(api.post)
      .mockReset()
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({
        data: {
          id: 'paper-uuid-001',
          project_id: PROJECT_ID,
          title: 'ACL reconstruction hamstring vs BPTB meta-analysis',
          duplicate: true,
          filename: 'paper.pdf',
          file_path: 'papers/paper.pdf',
          content_hash: 'abc123',
        },
      });

    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));

    const downloadBtns = screen.getAllByRole('button', { name: /Download OA PDF/i });
    fireEvent.click(downloadBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('↻ Already in project')).toBeInTheDocument();
    });
  });

  it('shows "Failed" with error message on download failure', async () => {
    vi.mocked(api.post)
      .mockReset()
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockRejectedValueOnce({
        response: { data: { detail: 'No se pudo resolver un PDF open-access' } },
      });

    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));

    const downloadBtns = screen.getAllByRole('button', { name: /Download OA PDF/i });
    fireEvent.click(downloadBtns[0]);

    await waitFor(() => {
      expect(screen.getByText('✗ Failed')).toBeInTheDocument();
    });
  });
});

describe('SearchPage — select and batch download flow', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ data: [] });
    vi.mocked(api.post).mockResolvedValue({ data: MOCK_RESPONSE });
  });

  it('Select all OA selects only downloadable papers', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL test');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));

    fireEvent.click(screen.getByRole('button', { name: /Select all OA/i }));

    // The first result is OA+doi → selectable. The second is closed → not selectable.
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes[0]).toBeChecked();
    // The second checkbox should be disabled (closed access) and not checked
    expect(checkboxes[1]).toBeDisabled();
  });

  it('Download Selected triggers /papers/batch-download with oa_url', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE }) // search
      .mockResolvedValueOnce({ data: { job_id: 'batch-job-001' } }); // batch

    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL test');
    fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));

    await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));

    fireEvent.click(screen.getByRole('button', { name: /Select all OA/i }));
    fireEvent.click(screen.getByRole('button', { name: /Download Selected/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/papers/batch-download',
        expect.objectContaining({
          project_id: PROJECT_ID,
          papers: expect.arrayContaining([
            expect.objectContaining({
              doi: '10.1000/test.001',
              pmid: '12345678',
              oa_url: 'https://ncbi.nlm.nih.gov/pmc/articles/PMC1234/pdf/',
            }),
          ]),
        }),
      );
    });
  });
});

describe('SearchPage — search history', () => {
  it('loads and displays search history on mount', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [
        {
          id: 'search-001',
          project_id: PROJECT_ID,
          query: 'hip fracture outcomes',
          source: 'federated',
          results_count: 15,
          executed_at: '2025-03-18T10:30:00Z',
        },
      ],
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Search History/i)).toBeInTheDocument();
    });
  });

  it('shows history entries when expanded', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [
        {
          id: 'search-001',
          project_id: PROJECT_ID,
          query: 'hip fracture outcomes',
          source: 'federated',
          results_count: 15,
          executed_at: '2025-03-18T10:30:00Z',
        },
      ],
    });

    renderPage();

    await waitFor(() => screen.getByText(/Search History/i));
    fireEvent.click(screen.getByText(/Search History/i));

    await waitFor(() => {
      expect(screen.getByText('hip fracture outcomes')).toBeInTheDocument();
      expect(screen.getByText(/15 results/)).toBeInTheDocument();
    });
  });
});
