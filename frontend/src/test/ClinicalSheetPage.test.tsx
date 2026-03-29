import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
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
  enqueueClinicalUpdate: vi.fn().mockResolvedValue({ job_id: 'update-1' }),
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
import { enqueueClinicalUpdate } from '../services/clinical';

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
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

describe('ClinicalSheetPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
        sources_used: {
          papers: [
            { paper_id: 'paper-1', doi: '10.1000/acl.1' },
            { paper_id: 'paper-2', pmid: '12345678' },
          ],
        },
        project_id: 'project-1',
      },
      toc: [],
      versions: [],
      evidenceSummary: { totalQuestions: 1, strengths: { high: 1, medium: 0, low: 0 } },
      error: null,
      refresh: vi.fn(),
      openVersion: vi.fn(),
    } as any);
    vi.mocked(api.post).mockResolvedValue({ data: { job_id: 'deck-1' } });
    vi.mocked(api.get).mockResolvedValue({ data: new Blob(['file']) });
  });

  it('renders project papers used in the sidebar', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Project papers used/i)).toBeInTheDocument();
      expect(screen.getByText('DOI: 10.1000/acl.1')).toBeInTheDocument();
      expect(screen.getByText('PMID: 12345678')).toBeInTheDocument();
    });
  });

  it('enqueues updates and presentation deck generation', async () => {
    renderPage();

    fireEvent.click(screen.getByRole('button', { name: 'Update sheet' }));
    await waitFor(() => {
      expect(enqueueClinicalUpdate).toHaveBeenCalledWith('sheet-1');
    });

    fireEvent.click(screen.getByRole('button', { name: 'Create deck' }));
    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/presentations/generate', {
        project_id: 'project-1',
        topic: 'ACL evidence',
        duration_minutes: 45,
        audience: 'universidad',
        paper_ids: ['paper-1', 'paper-2'],
        num_slides: 36,
      });
    });
  });
});
