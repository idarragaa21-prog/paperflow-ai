import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/search`]}>
        <Routes>
          <Route path="/projects/:projectId/search" element={<SearchPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const MOCK_RESPONSE = {
  count: 3,
  cached: false,
  sources: ['pubmed', 'europepmc', 'doaj'],
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
      abstract: 'Background: This study compares hamstring and BPTB grafts for ACL reconstruction. Methods: We conducted a systematic review. Results: Hamstring grafts showed comparable outcomes. Conclusion: Both methods are viable with trade-offs in donor site morbidity.',
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
    {
      pmid: null,
      pmcid: null,
      doi: '10.2000/doaj.003',
      title: 'Open access orthopedic biomechanics',
      authors: ['Lee C'],
      journal: 'DOAJ Open Ortho',
      pub_year: 2024,
      abstract: null,
      source: 'doaj',
      is_open_access: true,
      oa_url: 'https://doaj.org/article/test.pdf',
      relevance_score: 0.62,
    },
  ],
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Search for "ACL hamstring" and wait for results */
async function searchAndWait() {
  renderPage();
  await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
  fireEvent.click(screen.getByRole('button', { name: /^Search$/i }));
  await waitFor(() => screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis'));
}

// ── Global setup ────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.mocked(api.get).mockImplementation(async (url: string) => {
    if (url === `/projects/${PROJECT_ID}`) {
      return { data: { title: 'ACL project' } };
    }
    if (url === `/search/projects/${PROJECT_ID}/searches`) {
      return { data: [] };
    }
    return { data: [] };
  });
  vi.mocked(api.post).mockResolvedValue({ data: MOCK_RESPONSE });
});

afterEach(() => {
  vi.restoreAllMocks();
});

// ── 1. Render basics ────────────────────────────────────────────────────────

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
    expect(screen.getByRole('button', { name: /^Search$/i })).toBeDisabled();
  });

  it('search button is disabled with query shorter than 3 chars', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'AC');
    expect(screen.getByRole('button', { name: /^Search$/i })).toBeDisabled();
  });

  it('search button enables when query >= 3 chars', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL');
    expect(screen.getByRole('button', { name: /^Search$/i })).not.toBeDisabled();
  });
});

// ── 2. API call & payload ───────────────────────────────────────────────────

describe('SearchPage — API call', () => {
  it('calls /search/federated with correct payload', async () => {
    renderPage();
    await userEvent.type(screen.getByPlaceholderText(/ACL reconstruction/i), 'ACL hamstring');
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

  it('renders all result titles after search', async () => {
    await searchAndWait();
    expect(screen.getByText('ACL reconstruction hamstring vs BPTB meta-analysis')).toBeInTheDocument();
    expect(screen.getByText('Rotator cuff repair systematic review')).toBeInTheDocument();
    expect(screen.getByText('Open access orthopedic biomechanics')).toBeInTheDocument();
  });

  it('shows result count', async () => {
    await searchAndWait();
    expect(
      screen.getAllByText((_, element) => element?.textContent === '3 results · from pubmed, europepmc, doaj').length,
    ).toBeGreaterThan(0);
  });
});

// ── 3. Source badges & OA badges ────────────────────────────────────────────

describe('SearchPage — source and OA badges', () => {
  it('displays PubMed source badge', async () => {
    await searchAndWait();
    expect(screen.getByText('PubMed')).toBeInTheDocument();
  });

  it('displays Europe PMC source badge', async () => {
    await searchAndWait();
    expect(screen.getByText('Europe PMC')).toBeInTheDocument();
  });

  it('displays DOAJ source badge', async () => {
    await searchAndWait();
    expect(screen.getByText('DOAJ')).toBeInTheDocument();
  });

  it('displays OA badge for open access papers', async () => {
    await searchAndWait();
    const oaBadges = screen.getAllByText('OA');
    expect(oaBadges.length).toBe(2); // pubmed + doaj results are OA
  });

  it('displays Closed badge for non-OA papers', async () => {
    await searchAndWait();
    expect(screen.getByText('Closed')).toBeInTheDocument();
  });

  it('displays relevance score', async () => {
    await searchAndWait();
    expect(screen.getByText(/Score: 87%/)).toBeInTheDocument();
  });

  it('displays OA link for papers with oa_url', async () => {
    await searchAndWait();
    const oaLinks = screen.getAllByText('OA link ↗');
    expect(oaLinks.length).toBeGreaterThanOrEqual(1);
  });
});

// ── 4. Download eligibility ─────────────────────────────────────────────────

describe('SearchPage — download eligibility', () => {
  it('download button disabled for non-OA paper without identifiers', async () => {
    await searchAndWait();
    // Second result: europepmc, closed, doi only → no OA, button disabled
    const checkboxes = screen.getAllByRole('checkbox');
    // The europepmc result checkbox should be disabled (not OA)
    expect(checkboxes[1]).toBeDisabled();
  });

  it('download button enabled for OA paper with DOI', async () => {
    await searchAndWait();
    const downloadBtns = screen.getAllByRole('button', { name: /Download OA PDF/i });
    expect(downloadBtns[0]).not.toBeDisabled(); // first result: OA + DOI + PMID
  });
});

// ── 5. oa_url passthrough in download ───────────────────────────────────────

describe('SearchPage — oa_url in download payload', () => {
  it('sends oa_url to /papers/download', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({ data: { duplicate: false, filename: 'p.pdf', file_path: 'p.pdf', content_hash: 'h' } });

    await searchAndWait();
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

// ── 6. Filters ──────────────────────────────────────────────────────────────

describe('SearchPage — filters', () => {
  it('shows filter panel when Filters button is clicked', async () => {
    renderPage();
    await userEvent.click(screen.getByRole('button', { name: /Filters/i }));
    expect(screen.getByPlaceholderText(/e.g. Lancet/i)).toBeInTheDocument();
    expect(screen.getByText(/Open Access only/i)).toBeInTheDocument();
  });

  it('includes year_from filter in API payload', async () => {
    renderPage();
    await userEvent.click(screen.getByRole('button', { name: /Filters/i }));

    const yearFrom = screen.getByPlaceholderText('2018');
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
    renderPage();
    await userEvent.click(screen.getByRole('button', { name: /Filters/i }));

    // Find the OA checkbox specifically (not select-all checkboxes)
    const oaLabel = screen.getByText(/Open Access only/i);
    const oaCheckbox = oaLabel.parentElement?.querySelector('input[type="checkbox"]');
    expect(oaCheckbox).toBeTruthy();
    await userEvent.click(oaCheckbox!);

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

// ── 7. Error handling ───────────────────────────────────────────────────────

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

// ── 8. Download traceability ────────────────────────────────────────────────

describe('SearchPage — download traceability', () => {
  it('shows "Downloaded" with source after successful download', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({
        data: {
          id: 'paper-uuid-001', project_id: PROJECT_ID,
          title: 'ACL reconstruction hamstring vs BPTB meta-analysis',
          source_provider: 'unpaywall',
          oa_url: 'https://unpaywall.org/resolved.pdf',
          duplicate: false, filename: 'p.pdf', file_path: 'p.pdf', content_hash: 'h',
        },
      });

    await searchAndWait();
    fireEvent.click(screen.getAllByRole('button', { name: /Download OA PDF/i })[0]);

    await waitFor(() => {
      expect(screen.getByText(/Downloaded/)).toBeInTheDocument();
      expect(screen.getByText(/Unpaywall/)).toBeInTheDocument();
    });
  });

  it('shows resolved URL in traceability', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({
        data: {
          id: 'p1', project_id: PROJECT_ID, title: 'Test',
          source_provider: 'europepmc', oa_url: 'https://europepmc.org/pdf/123.pdf',
          duplicate: false, filename: 'p.pdf', file_path: 'p.pdf', content_hash: 'h',
        },
      });

    await searchAndWait();
    fireEvent.click(screen.getAllByRole('button', { name: /Download OA PDF/i })[0]);

    await waitFor(() => {
      expect(screen.getByText(/https:\/\/europepmc\.org\/pdf\/123\.pdf/)).toBeInTheDocument();
    });
  });

  it('shows "Already in project" for duplicates', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({
        data: {
          id: 'p1', project_id: PROJECT_ID, title: 'Test',
          duplicate: true, filename: 'p.pdf', file_path: 'p.pdf', content_hash: 'h',
        },
      });

    await searchAndWait();
    fireEvent.click(screen.getAllByRole('button', { name: /Download OA PDF/i })[0]);

    await waitFor(() => {
      expect(screen.getByText('↻ Already in project')).toBeInTheDocument();
    });
  });

  it('shows "Failed" on download error', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockRejectedValueOnce({ response: { data: { detail: 'No OA source' } } });

    await searchAndWait();
    fireEvent.click(screen.getAllByRole('button', { name: /Download OA PDF/i })[0]);

    await waitFor(() => {
      expect(screen.getByText('✗ Failed')).toBeInTheDocument();
    });
  });

  it('shows fallback warning when OA link failed and backend resolved differently', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({
        data: {
          id: 'p1', project_id: PROJECT_ID, title: 'Test',
          source_provider: 'unpaywall',
          oa_url: 'https://unpaywall.org/different-resolved.pdf',  // different from search result
          duplicate: false, filename: 'p.pdf', file_path: 'p.pdf', content_hash: 'h',
        },
      });

    await searchAndWait();
    fireEvent.click(screen.getAllByRole('button', { name: /Download OA PDF/i })[0]);

    await waitFor(() => {
      // The original oa_url was https://ncbi.nlm.nih.gov/pmc/articles/PMC1234/pdf/
      // The resolved is different → fallback detected
      expect(screen.getByText(/Downloaded \(fallback\)/)).toBeInTheDocument();
      // Shows the original failed URL
      expect(screen.getByText(/ncbi\.nlm\.nih\.gov/)).toBeInTheDocument();
    });
  });
});

// ── 9. Select and batch download ────────────────────────────────────────────

describe('SearchPage — select and batch download', () => {
  it('Select all OA selects only eligible papers', async () => {
    await searchAndWait();
    fireEvent.click(screen.getByRole('button', { name: /Select all OA/i }));

    const checkboxes = screen.getAllByRole('checkbox');
    // Result 1 (pubmed, OA) → checked
    expect(checkboxes[0]).toBeChecked();
    // Result 2 (europepmc, closed) → disabled
    expect(checkboxes[1]).toBeDisabled();
  });

  it('batch download sends oa_url in payload', async () => {
    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({ data: { job_id: 'batch-001' } });

    await searchAndWait();
    fireEvent.click(screen.getByRole('button', { name: /Select all OA/i }));
    fireEvent.click(screen.getByRole('button', { name: /Add \(2\) to Library/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/papers/batch-download',
        expect.objectContaining({
          project_id: PROJECT_ID,
          papers: expect.arrayContaining([
            expect.objectContaining({
              doi: '10.1000/test.001',
              oa_url: 'https://ncbi.nlm.nih.gov/pmc/articles/PMC1234/pdf/',
            }),
          ]),
        }),
      );
    });
  });

  it('shows a humanized batch failure message and preserves the technical detail', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === `/projects/${PROJECT_ID}`) {
        return { data: { title: 'ACL project' } };
      }
      if (url === `/search/projects/${PROJECT_ID}/searches`) {
        return { data: [] };
      }
      if (url === '/jobs/batch-001') {
        return {
          data: {
            status: 'completed',
            progress_percent: 100,
            result: {
              output: {
                items: [
                  {
                    title: 'Open access orthopedic biomechanics',
                    doi: '10.2000/doaj.003',
                    paper_id: null,
                    source_provider: 'doaj',
                    oa_url: 'https://doaj.org/article/test.pdf',
                    landing_url: 'https://doaj.org/article/test',
                    resolved_url: 'https://publisher.example.com/paper.pdf',
                    used_fallback: false,
                    final_status: 'failed',
                    failure_reason: "Client error '403 Forbidden' for url 'https://publisher.example.com/paper.pdf'",
                  },
                ],
                downloaded: [],
                already_exists: [],
                not_available: [],
                failed: [
                  {
                    title: 'Open access orthopedic biomechanics',
                    doi: '10.2000/doaj.003',
                    paper_id: null,
                    source_provider: 'doaj',
                    oa_url: 'https://doaj.org/article/test.pdf',
                    landing_url: 'https://doaj.org/article/test',
                    resolved_url: 'https://publisher.example.com/paper.pdf',
                    used_fallback: false,
                    final_status: 'failed',
                    failure_reason: "Client error '403 Forbidden' for url 'https://publisher.example.com/paper.pdf'",
                  },
                ],
              },
            },
          },
        };
      }
      return { data: [] };
    });

    vi.mocked(api.post)
      .mockResolvedValueOnce({ data: MOCK_RESPONSE })
      .mockResolvedValueOnce({ data: { job_id: 'batch-001' } });

    await searchAndWait();
    fireEvent.click(screen.getByRole('button', { name: /Select all OA/i }));
    fireEvent.click(screen.getByRole('button', { name: /Add \(2\) to Library/i }));

    await waitFor(() => {
      expect(screen.getByText(/La editorial o el proveedor bloquearon el acceso directo al PDF\./)).toBeInTheDocument();
      expect(screen.getByText(/Detalle técnico: .*403 Forbidden/)).toBeInTheDocument();
    });
  });
});

// ── 10. Search history ──────────────────────────────────────────────────────

describe('SearchPage — search history', () => {
  it('loads and displays search history on mount', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === `/projects/${PROJECT_ID}`) {
        return { data: { title: 'ACL project' } };
      }
      if (url === `/search/projects/${PROJECT_ID}/searches`) {
        return {
          data: [{
            id: 'search-001', project_id: PROJECT_ID,
            query: 'hip fracture outcomes', source: 'federated',
            results_count: 15, executed_at: '2025-03-18T10:30:00Z',
          }],
        };
      }
      return { data: [] };
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Search History/i)).toBeInTheDocument();
    });
  });

  it('shows entries when expanded', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === `/projects/${PROJECT_ID}`) {
        return { data: { title: 'ACL project' } };
      }
      if (url === `/search/projects/${PROJECT_ID}/searches`) {
        return {
          data: [{
            id: 'search-001', project_id: PROJECT_ID,
            query: 'hip fracture outcomes', source: 'federated',
            results_count: 15, executed_at: '2025-03-18T10:30:00Z',
          }],
        };
      }
      return { data: [] };
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
