import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('../services/cookies', () => ({
  getCookie: vi.fn(),
}));

import { api } from '../services/api';
import { getCookie } from '../services/cookies';
import { useAuthStore } from '../store/authStore';

describe('authStore.checkAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      loading: false,
      initialized: false,
      error: null,
    });
  });

  it('initializes without calling /auth/me when there is no session hint cookie', async () => {
    vi.mocked(getCookie).mockReturnValue(null);

    await useAuthStore.getState().checkAuth();

    expect(api.get).not.toHaveBeenCalled();
    expect(useAuthStore.getState()).toMatchObject({
      user: null,
      loading: false,
      initialized: true,
      error: null,
    });
  });

  it('loads the current user when the csrf cookie exists', async () => {
    vi.mocked(getCookie).mockReturnValue('csrf-token');
    vi.mocked(api.get).mockResolvedValue({
      data: { id: 'user-1', email: 'user@example.com', full_name: 'Dr. Vega' },
    });

    await useAuthStore.getState().checkAuth();

    expect(api.get).toHaveBeenCalledWith('/auth/me');
    expect(useAuthStore.getState().user).toEqual({
      id: 'user-1',
      email: 'user@example.com',
      full_name: 'Dr. Vega',
    });
  });
});
