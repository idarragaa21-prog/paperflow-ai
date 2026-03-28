import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ReferencesPage from '../pages/ReferencesPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

import { api } from '../services/api';

const PROJECT_ID = 'project-refs-1';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/references`]}>
      <Routes>
        <Route path="/projects/:projectId/references" element={<ReferencesPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ReferencesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
    vi.mocked(api.get).mockResolvedValue({
      data: [
        {
          id: 'ref-1',
          paper_id: 'paper-1',
          citation_key: 'smith2024',
          title: 'ACL outcomes after revision surgery',
          authors: ['Smith J', 'Lopez A'],
          journal: 'AJSM',
          publication_year: 2024,
          doi: '10.1000/acl.1',
          pmid: '123456',
          pmcid: null,
          source_format: 'bibtex',
        },
      ],
    });
    vi.mocked(api.post).mockResolvedValue({ data: { imported: 1, skipped: 0 } });
  });

  it('imports BibTeX content correctly', async () => {
    renderPage();

    fireEvent.change(await screen.findByTestId('references-content-input'), {
      target: { value: '@article{smith2024,title={ACL outcomes}}' },
    });
    fireEvent.click(screen.getByTestId('references-import-button'));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/references/import', {
        project_id: PROJECT_ID,
        format: 'bibtex',
        content: '@article{smith2024,title={ACL outcomes}}',
      });
    });
  });

  it('exports APA to the clipboard', async () => {
    renderPage();

    const button = await screen.findByRole('button', { name: 'Copy APA' });
    fireEvent.click(button);

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalled();
      expect(String(vi.mocked(navigator.clipboard.writeText).mock.calls[0][0])).toContain('ACL outcomes after revision surgery');
    });
  });

  it('filters requests by project id', async () => {
    renderPage();

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith('/references', {
        params: { project_id: PROJECT_ID },
      });
    });
  });
});
