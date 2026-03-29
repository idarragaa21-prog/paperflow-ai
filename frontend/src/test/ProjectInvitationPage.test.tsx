import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProjectInvitationPage from '../pages/ProjectInvitationPage';
import { useAuthStore } from '../store/authStore';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from '../services/api';

describe('ProjectInvitationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      loading: false,
      initialized: true,
      error: null,
    });
  });

  it('shows invitation details and public auth links for pending invitations', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        id: 'invite-1',
        project_id: 'project-1',
        project_title: 'RC Shared Project',
        email: 'invitee@example.com',
        role: 'viewer',
        status: 'pending',
      },
    });

    render(
      <MemoryRouter initialEntries={['/project-invitations/tok-abc']}>
        <Routes>
          <Route path="/project-invitations/:token" element={<ProjectInvitationPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('RC Shared Project')).toBeInTheDocument();
    });
    expect(screen.getByTestId('invitation-create-account-link')).toHaveAttribute(
      'href',
      '/signup?invitation_token=tok-abc&email=invitee%40example.com',
    );
    expect(screen.getByTestId('invitation-sign-in-link')).toHaveAttribute(
      'href',
      '/login?invitation_token=tok-abc&email=invitee%40example.com',
    );
  });

  it('lets the invited signed-in user open an already accepted shared project', async () => {
    useAuthStore.setState({
      user: { id: 'user-1', email: 'invitee@example.com', full_name: 'Invitee' },
      loading: false,
      initialized: true,
      error: null,
    });

    vi.mocked(api.get).mockResolvedValue({
      data: {
        id: 'invite-2',
        project_id: 'project-accepted',
        project_title: 'Accepted Project',
        email: 'invitee@example.com',
        role: 'viewer',
        status: 'accepted',
      },
    });

    render(
      <MemoryRouter initialEntries={['/project-invitations/tok-accepted']}>
        <Routes>
          <Route path="/project-invitations/:token" element={<ProjectInvitationPage />} />
          <Route path="/projects/:projectId/research" element={<div>Research home</div>} />
        </Routes>
      </MemoryRouter>,
    );

    const button = await screen.findByTestId('invitation-open-project-button');
    fireEvent.click(button);

    await waitFor(() => {
      expect(screen.getByText('Research home')).toBeInTheDocument();
    });
  });
});
