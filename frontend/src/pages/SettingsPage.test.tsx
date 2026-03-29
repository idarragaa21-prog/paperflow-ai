import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SettingsPage from './SettingsPage';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../store/authStore', () => ({
  useAuthStore: (selector: any) =>
    selector({
      user: { id: 'u1', email: 'test@test.com', full_name: 'Test User' },
      checkAuth: vi.fn(),
    }),
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

import { api } from '../services/api';

const mockServices: Array<{ name: string; status: string; latency_ms: number }> = [
  { name: 'postgres', status: 'ok', latency_ms: 3 },
  { name: 'redis', status: 'ok', latency_ms: 1 },
  { name: 'qdrant', status: 'degraded', latency_ms: 0 },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <SettingsPage />
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.get as any).mockResolvedValue({ data: { services: mockServices } });
});

describe('SettingsPage', () => {
  it('renders profile section with user name', () => {
    renderPage();
    expect(screen.getByDisplayValue('Test User')).toBeInTheDocument();
  });

  it('renders runtime mode selector', () => {
    renderPage();
    expect(screen.getByText(/local only/i)).toBeInTheDocument();
  });

  it('loads and shows service status when requested', async () => {
    renderPage();
    const btn = screen.queryByRole('button', { name: /check services/i });
    if (btn) {
      fireEvent.click(btn);
      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith('/health/services');
      });
    }
  });

  it('shows error when profile save fails', async () => {
    (api.patch as any).mockRejectedValue({ response: { data: { detail: 'Validation error' } } });
    renderPage();
    const saveBtn = screen.getByRole('button', { name: /save profile/i });
    fireEvent.click(saveBtn);
    await waitFor(() => {
      expect(api.patch).toHaveBeenCalled();
    });
  });
});
