import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import DraftsPage from '../pages/DraftsPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

import { api } from '../services/api';

const draft = {
  id: 'draft-1',
  title: 'ACL narrative synthesis',
  status: 'draft',
  version: 1,
  sections: [],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/project-1/drafts']}>
      <Routes>
        <Route path="/projects/:projectId/drafts" element={<DraftsPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('DraftsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/drafts') {
        return { data: [draft] };
      }
      if (url === '/evidence/tables') {
        return { data: [] };
      }
      return { data: [] };
    });
    vi.mocked(api.post).mockResolvedValue({ data: { ...draft, version: 2 } });
  });

  it('enriches the selected draft with clinical evidence', async () => {
    renderPage();

    const button = await screen.findByRole('button', { name: /enriquecer con evidencia/i });
    expect(button).not.toBeDisabled();

    await userEvent.click(button);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/drafts/draft-1/enhance-with-clinical');
    });
  });
});
