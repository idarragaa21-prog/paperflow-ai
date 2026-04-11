import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ClinicalPage from '../pages/ClinicalPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../components/Breadcrumb', () => ({
  Breadcrumb: () => <div data-testid="breadcrumb" />,
}));

import { api } from '../services/api';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/clinical']}>
        <Routes>
          <Route path="/clinical" element={<ClinicalPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ClinicalPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/projects') {
        return {
          data: [{ id: 'project-1', title: 'Stroke project', clinical_area: 'Neurology', archived: false }],
        };
      }
      if (url === '/clinical/consults') {
        return {
          data: [
            {
              id: 'consult-1',
              project_id: 'project-1',
              question: 'Should aspirin be used in secondary prevention?',
              mode: 'brief',
              status: 'completed',
              answer_markdown: 'Grounded answer',
              uncertainty_text: 'moderate',
              limitations_text: 'limited sources',
              used_project_library: true,
              used_pubmed: true,
              created_at: '2026-04-10T10:00:00Z',
              sources: [
                {
                  id: 'source-1',
                  source_kind: 'pubmed',
                  title: 'Aspirin trial',
                  pmid: '12345',
                  doi: null,
                  year: 2024,
                  excerpt: 'Aspirin reduced recurrent events.',
                  confidence: 0.8,
                },
              ],
              claims: [
                {
                  id: 'claim-1',
                  claim_text: 'Aspirin reduced recurrent events.',
                  confidence: 0.8,
                  support_level: 'supported',
                },
              ],
            },
          ],
        };
      }
      throw new Error(`Unexpected GET ${url}`);
    });
  });

  it('requires a question and creates consults through /clinical/consults', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        id: 'consult-new',
        project_id: null,
        question: 'Is aspirin useful after stroke?',
        mode: 'standard',
        status: 'completed',
        answer_markdown: 'answer',
        uncertainty_text: null,
        limitations_text: null,
        used_project_library: false,
        used_pubmed: true,
        created_at: '2026-04-10T10:00:00Z',
        sources: [],
        claims: [],
      },
    });

    renderPage();

    const submit = await screen.findByRole('button', { name: 'Generate consult' });
    expect(submit).toBeDisabled();

    await userEvent.type(
      screen.getByPlaceholderText('e.g. Should aspirin be used for secondary prevention after ischemic stroke?'),
      'Is aspirin useful after stroke?',
    );
    expect(screen.getByRole('button', { name: 'Generate consult' })).not.toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Generate consult' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith(
        '/clinical/consults',
        expect.objectContaining({
          question: 'Is aspirin useful after stroke?',
        }),
      );
    });
  });

  it('renders claims and sources from recent consults', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Aspirin trial')).toBeInTheDocument();
      expect(screen.getAllByText('Aspirin reduced recurrent events.').length).toBeGreaterThan(0);
      expect(screen.getByText('Grounded answer')).toBeInTheDocument();
    });
  });
});
