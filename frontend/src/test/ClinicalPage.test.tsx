import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ClinicalPage from '../pages/ClinicalPage';
import ClinicalSheetPage from '../pages/ClinicalSheetPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../components/Breadcrumb', () => ({
  Breadcrumb: () => <div data-testid="breadcrumb" />,
}));

vi.mock('../domain/clinical/hooks/useClinicalSheet', () => ({
  useClinicalSheet: vi.fn(),
}));

vi.mock('../components/clinical/ClinicalProViewer', () => ({
  default: ({ pro }: { pro: { title: string } }) => <div>ClinicalProViewer {pro.title}</div>,
}));

vi.mock('../domain/clinical/components/EvidenceDrawer', () => ({
  default: () => <div>Evidence drawer</div>,
}));

vi.mock('../services/clinical', () => ({
  enqueueClinicalUpdate: vi.fn(),
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

vi.mock('../ui/Dialog/useConfirm', () => ({
  useConfirm: () => vi.fn().mockResolvedValue(true),
}));

vi.mock('../ui/Skeleton/Skeleton', () => ({
  Skeleton: () => <div data-testid="skeleton" />,
  SkeletonLines: () => <div data-testid="skeleton-lines" />,
}));

import { api } from '../services/api';
import { useClinicalSheet } from '../domain/clinical/hooks/useClinicalSheet';

const PROJECT_ID = 'clinical-project-1';

function renderClinicalPage() {
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

function renderClinicalSheetPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/clinical/sheets/sheet-1']}>
        <Routes>
          <Route path="/clinical/sheets/:sheetId" element={<ClinicalSheetPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ClinicalPage and ClinicalSheetPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/projects') {
        return {
          data: [{ id: PROJECT_ID, title: 'ACL Project', clinical_area: 'Sports Medicine', archived: false }],
        };
      }
      if (url === `/projects/${PROJECT_ID}/dashboard`) {
        return { data: { counts: { papers: 6 } } };
      }
      if (url === '/clinical/sheets') {
        return { data: [] };
      }
      return { data: [] };
    });
  });

  it('validates required form fields before generation', async () => {
    renderClinicalPage();

    const button = await screen.findByRole('button', { name: 'Generate Clinical Sheet' });
    expect(button).toBeDisabled();

    await userEvent.type(
      screen.getByPlaceholderText(/Fifth metatarsal stress fracture/i),
      'ACL graft failure',
    );

    expect(screen.getByRole('button', { name: 'Generate Clinical Sheet' })).not.toBeDisabled();
  });

  it('shows a spinner state while generation is starting', async () => {
    let resolveRequest!: (value: { data: { job_id: string } }) => void;
    vi.mocked(api.post).mockImplementation(
      () =>
        new Promise<{ data: { job_id: string } }>((resolve) => {
          resolveRequest = resolve;
        }),
    );

    renderClinicalPage();

    await userEvent.type(screen.getByPlaceholderText(/Fifth metatarsal stress fracture/i), 'Meniscus tear');
    fireEvent.click(screen.getByRole('button', { name: 'Generate Clinical Sheet' }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Starting…' })).toBeInTheDocument();
    });

    resolveRequest({ data: { job_id: 'job-1' } });
  });

  it('renders ClinicalProViewer with the expected data on the sheet page', async () => {
    vi.mocked(useClinicalSheet).mockReturnValue({
      status: 'ready',
      sheet: {
        id: 'sheet-1',
        topic: 'ACL evidence',
        version: 2,
        is_current: true,
        format_version: 'clinical_pro_v1',
        content_markdown: '',
        content_json: { title: 'ACL Pro Output' },
        sources_used: {},
        project_id: PROJECT_ID,
      },
      toc: [],
      versions: [],
      evidenceSummary: { totalQuestions: 1, strengths: { high: 1, medium: 0, low: 0 } },
      error: null,
      refresh: vi.fn(),
      openVersion: vi.fn(),
    } as any);

    renderClinicalSheetPage();

    await waitFor(() => {
      expect(screen.getByText('ClinicalProViewer ACL Pro Output')).toBeInTheDocument();
    });
  });
});
