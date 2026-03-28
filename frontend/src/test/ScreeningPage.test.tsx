import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ScreeningPage from '../pages/ScreeningPage';
import { useAuthStore } from '../store/authStore';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from '../services/api';

const PROJECT_ID = 'screening-project-1';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/screening`]}>
      <Routes>
        <Route path="/projects/:projectId/screening" element={<ScreeningPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ScreeningPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: { id: 'user-viewer', email: 'viewer@example.com', full_name: 'Viewer User' },
      loading: false,
      initialized: true,
      error: null,
    });

    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/screening/batches') return { data: [] };
      if (url === '/screening/reasons') return { data: [] };
      if (url === `/projects/${PROJECT_ID}/library`) return { data: [{ id: 'paper-1', title: 'Fixture paper' }] };
      if (url === '/screening/prisma') return { data: { counts: {} } };
      if (url === `/projects/${PROJECT_ID}/members`) {
        return {
          data: [
            { user_id: 'user-owner', email: 'owner@example.com', project_id: PROJECT_ID, role: 'owner' },
            { user_id: 'user-viewer', email: 'viewer@example.com', project_id: PROJECT_ID, role: 'viewer' },
          ],
        };
      }
      return { data: [] };
    });
    vi.mocked(api.post).mockResolvedValue({ data: { ok: true } });
  });

  it('keeps batch creation disabled for viewers while collaboration actions remain available', async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId('screening-create-batch')).toBeDisabled();
      expect(screen.getByTestId('screening-add-comment')).toBeEnabled();
      expect(screen.getByTestId('screening-queue-review-action')).toBeEnabled();
    });
  });

  it('queues a review action with the selected paper', async () => {
    renderPage();

    const reviewButton = await screen.findByTestId('screening-queue-review-action');
    fireEvent.click(reviewButton);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/screening/peer-review-actions', {
        project_id: PROJECT_ID,
        action: 'screening_review',
        status: 'open',
        payload_json: {
          paper_id: 'paper-1',
          batch_id: null,
          stage: 'title_abstract',
        },
      });
    });
  });

  it('validates comment content when the button is clicked empty', async () => {
    renderPage();

    const commentButton = await screen.findByTestId('screening-add-comment');
    await userEvent.click(commentButton);

    await waitFor(() => {
      expect(screen.getByText('Write a comment before adding it to the screening workflow.')).toBeInTheDocument();
    });
  });
});
