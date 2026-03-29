import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPage from '../pages/SettingsPage';
import { useAuthStore } from '../store/authStore';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('../ui/Toast/ToastProvider', () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn() }),
}));

vi.mock('../i18n', () => ({
  useI18n: () => ({
    t: { settings: { title: 'Settings', language: 'Language', languageDesc: 'Choose a language' } },
    locale: 'en',
    setLocale: vi.fn(),
    localeNames: { en: 'English', es: 'Español' },
  }),
}));

vi.mock('../components/ThemeProvider', () => ({
  useTheme: () => ({ theme: 'light', setTheme: vi.fn() }),
}));

import { api } from '../services/api';

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    useAuthStore.setState({
      user: { id: 'user-1', email: 'owner@example.com', full_name: 'Owner User' },
      loading: false,
      initialized: true,
      error: null,
      checkAuth: vi.fn().mockResolvedValue(undefined),
    } as any);

    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/health/services') {
        return { data: { services: { ollama: { status: 'ok', latency_ms: 22 }, grobid: { status: 'ok', latency_ms: 80 } } } };
      }
      if (url === '/billing/usage') {
        return {
          data: {
            period: 'monthly',
            month: '2026-03',
            tier: 'local',
            quota_calls: 1000,
            calls_used: 12,
            quota_remaining: 988,
            tokens_in: 100,
            tokens_out: 40,
            total_tokens: 140,
            cost_usd: 0.03,
            models: [{ model: 'llama3', calls: 12, tokens_in: 100, tokens_out: 40, total_tokens: 140 }],
            recent: [],
          },
        };
      }
      if (url === '/billing/history') {
        return { data: { months: [{ month: '2026-02', calls: 8, tokens_in: 50, tokens_out: 20, total_tokens: 70, cost_usd: 0.01 }] } };
      }
      if (url === '/projects') {
        return { data: [{ id: 'project-1', title: 'ACL Project', archived: false }] };
      }
      if (url === '/projects/project-1/members') {
        return { data: [{ project_id: 'project-1', user_id: 'user-1', email: 'owner@example.com', full_name: 'Owner User', role: 'owner' }] };
      }
      throw new Error(`Unexpected GET ${url}`);
    });
    vi.mocked(api.post).mockResolvedValue({ data: { kind: 'membership', member: { user_id: 'member-2' } } });
    vi.mocked(api.patch).mockResolvedValue({ data: {} });
  });

  it('loads service and usage sections and persists runtime mode locally', async () => {
    render(<SettingsPage />);

    await waitFor(() => {
      expect(screen.getByText('ollama')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'Uso local & cuotas' }));
    await waitFor(() => {
      expect(screen.getByText(/Estimated local cost/i)).toBeInTheDocument();
      expect(screen.getByText('llama3')).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole('button', { name: 'General' }));
    const hybridLabel = await screen.findByText('Hybrid');
    const hybridRadio = hybridLabel.closest('label')?.querySelector('input[type="radio"]') as HTMLInputElement | null;
    expect(hybridRadio).toBeTruthy();
    fireEvent.click(hybridRadio!);
    expect(localStorage.getItem('pf_runtime_mode')).toBe('hybrid');
  });

  it('blocks password change when confirmation does not match', async () => {
    render(<SettingsPage />);

    const inputs = screen.getAllByDisplayValue('');
    await userEvent.type(inputs[0], 'current-password');
    await userEvent.type(inputs[1], 'new-password');
    await userEvent.type(inputs[2], 'different-password');
    fireEvent.click(screen.getByRole('button', { name: 'Update password' }));

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    });
  });

  it('validates invite email before sending a team invitation', async () => {
    render(<SettingsPage />);

    await userEvent.click(screen.getByRole('button', { name: 'Equipo' }));
    await waitFor(() => expect(screen.getByText('Team management')).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText('researcher@example.com'), 'invalid-email');
    fireEvent.click(screen.getByRole('button', { name: 'Invite member' }));

    await waitFor(() => {
      expect(screen.getByText('Enter a valid email.')).toBeInTheDocument();
    });
  });
});
