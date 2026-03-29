import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CollaborationPage from '../pages/CollaborationPage';
import { useAuthStore } from '../store/authStore';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { api } from '../services/api';

const PROJECT_ID = 'project-123';
const OWNER_ID = 'owner-1';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/collaboration`]}>
      <Routes>
        <Route path="/projects/:projectId/collaboration" element={<CollaborationPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('CollaborationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: { id: OWNER_ID, email: 'owner@example.com', full_name: 'Owner User' },
      loading: false,
      initialized: true,
      error: null,
    });

    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === `/projects/${PROJECT_ID}/members`) {
        return {
          data: [
            {
              project_id: PROJECT_ID,
              user_id: OWNER_ID,
              email: 'owner@example.com',
              full_name: 'Owner User',
              role: 'owner',
            },
          ],
        };
      }
      if (url === `/projects/${PROJECT_ID}/invitations`) {
        return { data: [] };
      }
      return { data: [] };
    });
  });

  it('shows that an invitation email was sent when SMTP delivery succeeds', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        kind: 'invitation',
        invitation: { token: 'tok-123', accept_path: '/project-invitations/tok-123' },
        invitation_url: 'https://app.paperflow.ai/project-invitations/tok-123',
        delivery_status: 'sent',
        delivery_method: 'smtp',
      },
    });

    renderPage();

    await userEvent.type(await screen.findByTestId('member-email-input'), 'invitee@example.com');
    fireEvent.click(screen.getByTestId('member-add-button'));

    await waitFor(() => {
      expect(screen.getByText(/will receive an invitation email shortly/i)).toBeInTheDocument();
    });
  });

  it('falls back to a manual secure link when email delivery is not configured', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    vi.mocked(api.post).mockResolvedValue({
      data: {
        kind: 'invitation',
        invitation: { token: 'tok-456', accept_path: '/project-invitations/tok-456' },
        invitation_url: 'https://app.paperflow.ai/project-invitations/tok-456',
        delivery_status: 'manual_required',
        delivery_method: 'manual_link',
      },
    });

    renderPage();

    await userEvent.type(await screen.findByTestId('member-email-input'), 'invitee@example.com');
    fireEvent.click(screen.getByTestId('member-add-button'));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith('https://app.paperflow.ai/project-invitations/tok-456');
      expect(screen.getByText(/invitation link copied/i)).toBeInTheDocument();
    });
  });
});
